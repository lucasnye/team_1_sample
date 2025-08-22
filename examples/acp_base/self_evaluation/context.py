#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EDGAR Form D → 3 similar startups → Gemini enrichment (function-calling, resilient)

Usage:
  export GEMINI_API_KEY="..."
  export SEC_USER_EMAIL="you@example.com"
  python find_similar_startups.py --sic 7372 --companies 3

What it does:
  1) Discover many CIKs by SIC (browse-edgar HTML)
  2) For each CIK, find the most recent Form D via data.sec.gov submissions JSON
  3) Fetch the real XML via .../index.json and parse core facts deterministically
  4) Pick 3 “similar” startups (same industryGroup + state/country when possible)
  5) For each, call Gemini using function-calling to fill ONLY soft fields
  6) Print a JSON array of the 3 enriched profiles
"""

import os
import re
import json
import time
import random
import argparse
import threading
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import base64

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==============================
# Config
# ==============================
APP_NAME_VERSION = "LucasNg-EDGAR-3Similar/2.0"
CONTACT_EMAIL    = os.getenv("CONTACT_EMAIL") # os.environ.get("SEC_USER_EMAIL", "email@example.com")
USER_AGENT       = f"{APP_NAME_VERSION} (+mailto:{CONTACT_EMAIL})"

BASE_SEC_URL = "https://www.sec.gov"
DATA_SEC_URL = "https://data.sec.gov"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = "gemini-2.5-flash"
GEMINI_URL     = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

# pacing
SEC_RPM        = 60
GEMINI_RPM     = 6
ENRICH_SLEEP_S = (2.0, 3.5)  # delay between Gemini calls (gentle)

# ==============================
# HTTP session + limiter
# ==============================
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    retry = Retry(
        total=5, connect=5, read=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET","POST"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter); s.mount("http://", adapter)
    return s

SESSION = make_session()

class TokenBucket:
    def __init__(self, rpm: int, label: str):
        self.capacity = rpm
        self.tokens   = rpm
        self.refill   = rpm / 60.0  # per second
        self.label    = label
        self.last     = time.monotonic()
        self.lock     = threading.Lock()
    def acquire(self):
        with self.lock:
            now = time.monotonic()
            dt  = now - self.last
            self.last = now
            self.tokens = min(self.capacity, self.tokens + dt * self.refill)
            if self.tokens < 1:
                need = (1 - self.tokens) / self.refill
                time.sleep(need + random.uniform(0.02, 0.06))
                self.last = time.monotonic()
                self.tokens = max(0.0, self.tokens + need*self.refill - 1)
            else:
                self.tokens -= 1

SEC_BUCKET    = TokenBucket(SEC_RPM, "SEC")
GEMINI_BUCKET = TokenBucket(GEMINI_RPM, "GEMINI")

def parse_retry_after(resp: requests.Response) -> Optional[float]:
    v = resp.headers.get("Retry-After")
    if not v: return None
    try: return float(v)
    except: return 10.0

def safe_get(url: str, **kw) -> requests.Response:
    if "sec.gov" in url:
        SEC_BUCKET.acquire()
    resp = SESSION.get(url, timeout=60, **kw)
    if resp.status_code == 429:
        ra = parse_retry_after(resp) or (2.0 + random.uniform(0,1))
        who = "SEC" if "sec.gov" in url else "OTHER"
        print(f"[{who}] 429; sleeping {ra:.1f}s")
        time.sleep(ra)
    return resp

def safe_post(url: str, **kw) -> requests.Response:
    if "googleapis.com" in url:
        GEMINI_BUCKET.acquire()
    resp = SESSION.post(url, timeout=90, **kw)
    if resp.status_code == 429:
        ra = parse_retry_after(resp) or (8.0 + random.uniform(0,4))
        print(f"[GEMINI] 429; sleeping {ra:.1f}s")
        time.sleep(ra)
    return resp

# ==============================
# EDGAR helpers
# ==============================
def get_ciks_by_sic(sic_code: str, max_companies: int = 50) -> List[int]:
    """Scrape CIKs from browse-edgar HTML for a given SIC."""
    url = (f"{BASE_SEC_URL}/cgi-bin/browse-edgar?"
           f"action=getcompany&SIC={sic_code}&owner=exclude&count={max_companies}")
    r = safe_get(url); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    ciks = []
    for row in soup.select("table.tableFile2 tr")[1:]:
        a = row.find("a", href=True)
        if not a: continue
        txt = a.text.strip()
        try:
            ciks.append(int(txt.lstrip("0")))
        except:
            pass
    # dedupe, preserve order
    out = []
    seen = set()
    for c in ciks:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out

def submissions_json(cik: int) -> dict:
    url = f"{DATA_SEC_URL}/submissions/CIK{cik:010d}.json"
    r = safe_get(url); r.raise_for_status()
    return r.json()

def recent_form_d(cik: int) -> Optional[Dict[str, str]]:
    """Return the most recent Form D metadata (accno, date, primaryDoc), or None."""
    data = submissions_json(cik)
    rec = data.get("filings", {}).get("recent", {})
    forms = rec.get("form", []) or []
    for i, ft in enumerate(forms):
        if str(ft).strip().upper() == "D":
            accno = rec["accessionNumber"][i].replace("-", "")
            date  = rec["filingDate"][i]
            prim  = rec["primaryDocument"][i]
            idx   = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accno}-index.html"
            doc   = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accno}/{prim}"
            return {"accno": accno, "date": date, "index_url": idx, "doc_url": doc}
    return None

def dir_index_items(cik: int, accno: str) -> List[Dict[str, Any]]:
    url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accno}/index.json"
    r = safe_get(url, headers={"Accept":"application/json"})
    if not r.ok: return []
    try:
        j = r.json()
        return j.get("directory", {}).get("item", []) or []
    except:
        return []

def pick_form_d_xml_url(cik: int, accno: str, primary_doc: Optional[str]) -> Optional[str]:
    items = dir_index_items(cik, accno)
    names = [it.get("name","") for it in items]
    def mk(n): return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accno}/{n}"
    if "primary_doc.xml" in names: return mk("primary_doc.xml")
    if "xslFormDX01" in names:     return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accno}/xslFormDX01/primary_doc.xml"
    xmls = [n for n in names if n.lower().endswith(".xml")]
    xmls.sort(key=lambda n: (not any(k in n.lower() for k in ["primary","form","d"]), len(n)))
    if xmls: return mk(xmls[0])
    if primary_doc and primary_doc.lower().endswith(".xml"):
        return mk(primary_doc)
    return None

def fetch_form_d_text(cik: int, meta: Dict[str,str]) -> str:
    """Return raw XML/HTML text of Form D primary doc."""
    xml_url = pick_form_d_xml_url(cik, meta["accno"], meta.get("doc_url"))
    headers = {"Accept": "application/xml, text/html;q=0.8"}
    if xml_url:
        r = safe_get(xml_url, headers=headers)
        if r.ok and (r.headers.get("Content-Type","").lower().find("xml")>=0 or r.text.strip().startswith("<")):
            return r.text
    # fallback to primary doc or index 1st row
    if meta.get("doc_url"):
        r = safe_get(meta["doc_url"], headers=headers); r.raise_for_status(); return r.text
    r = safe_get(meta["index_url"]); r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table", {"summary":"Document Format Files"})
    rows = table.find_all("tr") if table else []
    if len(rows) >= 2:
        a = rows[1].find("a", href=True)
        if a:
            url = urljoin(BASE_SEC_URL, a["href"])
            r2 = safe_get(url, headers=headers); r2.raise_for_status(); return r2.text
    raise RuntimeError("No Form D document found")

# ==============================
# Parsing helpers (lenient XML)
# ==============================
def _xml_lenient(s: str):
    try: return ET.fromstring(s)
    except: pass
    try:
        from lxml import etree as LET
        p = LET.XMLParser(recover=True, huge_tree=True)
        return LET.fromstring(s.encode("utf-8","ignore"), parser=p)
    except: pass
    try:
        bs = BeautifulSoup(s, "xml")
        rt = bs.find()
        if not rt: return None
        def build(el):
            node = ET.Element(el.name if el.name else "node")
            if el.string and el.string.strip():
                node.text = el.string.strip()
            for ch in el.find_all(recursive=False):
                if ch.name: node.append(build(ch))
            return node
        return build(rt)
    except: return None

def _t(el) -> Optional[str]:
    if el is None: return None
    v = (el.text or "").strip()
    return v or None

def _find_any(root, paths: List[str]):
    for p in paths:
        try: el = root.find(p)
        except: el = None
        if el is not None: return el
    tgt = paths[0].split("/")[-1].lower()
    try: it = root.iter()
    except: it = []
    for el in it:
        tag = getattr(el, "tag", "")
        if str(tag).lower().endswith(tgt): return el
    return None

def parse_form_d(xml_text: str) -> Dict[str,Any]:
    root = _xml_lenient(xml_text)
    if root is None: raise ValueError("Unparseable XML")

    def T(paths): return _t(_find_any(root, paths))

    issuer   = T([".//issuer/issuerName", ".//primaryIssuer/issuerName"])
    city     = T([".//issuer/issuerAddress/city"])
    state    = T([".//issuer/issuerAddress/stateOrCountry"])
    state_d  = T([".//issuer/issuerAddress/stateOrCountryDescription"])
    country  = T([".//issuer/issuerAddress/country"])
    hq_parts = [p for p in [city, state_d or state, country] if p]
    hq       = ", ".join(hq_parts) if hq_parts else None

    industry = T([".//industryGroup/industryGroupType", ".//industryGroup/industryGroupDesc"])
    ent_type = T([".//issuer/entityType"])
    phone    = T([".//issuer/issuerPhoneNumber"])

    tot_off  = T([".//offeringData/totalOfferingAmount"])
    tot_sold = T([".//offeringData/totalAmountSold"])
    first    = T([".//offeringData/dateOfFirstSale/value"])
    amend    = T([".//offeringData/typeOfFiling/isAmendment"])

    # related persons (very lenient)
    people = []
    try:
        it = root.iter()
    except: it = []
    for node in it:
        if str(getattr(node, "tag","")).lower().endswith("relatedpersoninfo"):
            f = getattr(node, "find", None)
            nm = _t(f("./relatedPersonName/fullName")) if f else None
            if not nm and f: nm = _t(f("./relatedPersonName/firstName"))
            title = _t(f("./relatedPersonRelationshipList/relationship")) if f else None
            if nm: people.append({"name": nm, "title": title})

    desc = []
    if issuer:     desc.append(f"{issuer} filed a Form D.")
    if industry:   desc.append(f"Industry group: {industry}.")
    if hq:         desc.append(f"HQ: {hq}.")
    if tot_off:    desc.append(f"Offering total: {tot_off}.")
    if tot_sold:   desc.append(f"Sold: {tot_sold}.")
    if first:      desc.append(f"First sale: {first}.")
    description = " ".join(desc) or None

    return {
        "company_name": issuer,
        "industry": industry,
        "subsector": None,
        "stage": None,
        "hq_location": hq,
        "business_model": None,
        "markets": None,
        "moat": None,
        "go_to_market": None,
        "tech_stack": None,
        "description": description,
        "keywords": [k for k in [industry, "Form D", "private offering"] if k],
        "profitability": None,
        "growth_rate": None,
        "_formd": {
            "entity_type": ent_type,
            "phone": phone,
            "total_offering_amount": tot_off,
            "total_amount_sold": tot_sold,
            "date_of_first_sale": first,
            "is_amendment": amend,
            "people": people or None,
        }
    }

# ==============================
# Similarity selector
# ==============================
def choose_3_similar(profiles: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    """
    Prefer same (industry, state/country). If tie, pick earliest filing date.
    Profiles items must include keys: industry, _geo (state/country), _filing_date
    """
    # attach geo key
    for p in profiles:
        geo = None
        hq  = p.get("hq_location") or ""
        # crude: last token as country/state code
        m = re.findall(r"[A-Z]{2,}", hq)
        if m: geo = m[-1]
        p["_geo"] = geo

    # group by (industry, geo)
    buckets = {}
    for p in profiles:
        key = (p.get("industry") or "Unknown", p.get("_geo") or "Unknown")
        buckets.setdefault(key, []).append(p)

    # pick largest bucket with at least 3
    best_key = None
    best_len = 0
    for k, arr in buckets.items():
        if len(arr) > best_len:
            best_len = len(arr); best_key = k

    if best_key and best_len >= 3:
        arr = buckets[best_key]
        arr.sort(key=lambda x: x.get("_filing_date",""))
        return arr[:3]

    # else: take top 3 overall by most common (industry), then earliest filing
    profiles.sort(key=lambda x: (x.get("industry") or "", x.get("_filing_date","")))
    return profiles[:3]

# ==============================
# Gemini function-calling
# ==============================
def heuristic_enrich(company: Dict[str,Any], wiki: Optional[str]) -> Dict[str,Any]:
    fd = company.get("_formd") or {}
    def _to_float(s):
        try: return float(re.sub(r"[,$_\s]", "", s)) if s else None
        except: return None
    amt = _to_float(fd.get("total_offering_amount"))
    fs  = (fd.get("date_of_first_sale") or "").strip() or None
    yr  = int(fs[:4]) if fs and re.match(r"^\d{4}-\d{2}-\d{2}$", fs) else None
    desc = " ".join([company.get("description") or "", wiki or ""]).lower()

    # ---- stage (very rough; you can tune thresholds)
    stage = None
    if amt is not None:
        if amt < 2_000_000: stage = "Seed"
        elif amt < 7_000_000: stage = "Series A"
        elif amt < 15_000_000: stage = "Series B"
        elif amt < 50_000_000: stage = "Series C"
        else: stage = "Late"
    if "ipo" in desc or (yr and yr < 2012 and amt and amt > 20_000_000):
        stage = stage or "Late"

    # ---- business model (simple keyword map)
    bm = None
    if any(k in desc for k in ["saas","software","cloud","b2b"]): bm = "B2B SaaS"
    elif any(k in desc for k in ["marketplace","platform","buyers","sellers"]): bm = "Marketplace"
    elif any(k in desc for k in ["payments","fintech","bank","lending"]): bm = "Fintech"
    elif any(k in desc for k in ["security","authentication","identity","smart card"]): bm = "Cybersecurity"
    # Adaptive defaults by name hints
    nm = (company.get("company_name") or "").lower()
    if not bm and "adaptive insights" in nm: bm = "B2B SaaS"
    if not bm and "active network" in nm: bm = "B2B SaaS"
    if not bm and "actividentity" in nm: bm = "Cybersecurity"

    patch = {}
    if stage: patch["stage"] = stage
    if bm:    patch["business_model"] = bm
    return patch


def wiki_summary(name: str) -> Optional[str]:
    """Fetch a one-line Wikipedia summary for the company name (best-effort)."""
    if not name: return None
    # Trim corporate suffixes to improve hit rate
    q = re.sub(r"\b(incorporated|inc\.?|corp\.?|corporation|ltd\.?|llc)\b", "", name, flags=re.I).strip()
    if not q: q = name.strip()
    # 1) search
    try:
        r = safe_get(f"https://en.wikipedia.org/w/rest.php/v1/search/title?q={requests.utils.quote(q)}&limit=1",
                     headers={"Accept":"application/json"})
        if not r.ok: return None
        j = r.json()
        if not (j.get("pages")): return None
        slug = j["pages"][0].get("key")
        if not slug: return None
        # 2) summary
        r2 = safe_get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(slug)}",
                      headers={"Accept":"application/json"})
        if not r2.ok: return None
        j2 = r2.json()
        extract = (j2.get("extract") or "").strip()
        if extract:
            # keep it short
            return re.split(r"\s*\.\s*", extract, maxsplit=1)[0][:280]
    except Exception:
        return None
    return None


def gemini_fill_soft(company: Dict[str,Any]) -> Dict[str,Any]:
    if not GEMINI_API_KEY:
        company["_enrichment_status"] = "skipped_no_api_key"
        company["_enriched_keys"] = []
        return company

    # --- tiny external snippet (optional) ---
    wiki = wiki_summary(company.get("company_name") or "")

    # --- compact facts (safe to serialize) ---
    fd = company.get("_formd") or {}
    def _to_float(s):
        try: return float(re.sub(r"[,$_\s]", "", s)) if s else None
        except: return None
    facts = {
        "company_name": company.get("company_name"),
        "industry": company.get("industry"),
        "hq_location": company.get("hq_location"),
        "description": (company.get("description") or "")[:220],
        "funding_amount_usd": _to_float(fd.get("total_offering_amount")),
        "first_sale_year": int((fd.get("date_of_first_sale") or "")[:4]) if (fd.get("date_of_first_sale") or "").startswith(tuple("0123456789")) else None,
        "wiki": wiki
    }
    facts = {k:v for k,v in facts.items() if v not in (None, "", [], {})}

    fillable = ["stage","business_model","subsector","markets","moat","go_to_market",
                "tech_stack","keywords","profitability","growth_rate"]

    # ---------- IMPORTANT: lower-case types for function params ----------
    STR   = {"type": "string"}
    NUM   = {"type": "number"}
    ARR_S = {"type": "array", "items": {"type": "string"}}
    type_map = {"markets": ARR_S, "tech_stack": ARR_S, "keywords": ARR_S, "growth_rate": NUM}
    props = {k: type_map.get(k, STR) for k in fillable}

    tools = [{
        "functionDeclarations": [{
            "name": "fill_company_fields",
            "description": "Infer concise values from facts + public knowledge; keep it short. If unsure, omit that key.",
            "parameters": {
                "type": "object",
                "properties": props
            }
        }]
    }]

    prompt = (
        "Enrich this startup profile using the facts and your public world knowledge as of 2025. "
        "Call fill_company_fields and return only keys you can infer (short phrases). "
        "Prefer to include at least 'stage' and 'business_model' if reasonably inferable.\n"
        f"facts={json.dumps(facts, ensure_ascii=False)}"
    )

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": tools,
        # ---------- IMPORTANT: valid enum and pin the function name ----------
        "toolConfig": {"functionCallingConfig": {
            "mode": "ANY",
            "allowedFunctionNames": ["fill_company_fields"]
        }},
        "generationConfig": {"temperature": 0.2, "topK": 1, "topP": 0.1, "maxOutputTokens": 220}
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}

    applied: Dict[str,Any] = {}
    try:
        r = safe_post(GEMINI_URL, headers=headers, json=body)
        # Print *why* on 400
        if r.status_code == 400:
            try:
                print(f"[GEMINI][400] response: {r.text}")
            except Exception:
                pass
        if r.status_code == 429:
            ra = parse_retry_after(r) or (8 + random.uniform(0,4))
            print(f"[GEMINI] 429; sleeping {ra:.1f}s")
            time.sleep(ra)
            r = safe_post(GEMINI_URL, headers=headers, json=body)

        r.raise_for_status()
        data = r.json()

        # Parse function-call style output (your existing helper)
        patch = _extract_gemini_payload(data)  # must return a dict of key->value if present

        if isinstance(patch, dict):
            for k in fillable:
                v = patch.get(k, None)
                if v not in (None, "", [], {}):
                    company[k] = v
                    applied[k] = v

    except Exception as e:
        print(f"[GEMINI] error: {e}")

    # Fallback heuristics if model returned nothing usable
    if not applied:
        h = heuristic_enrich(company, wiki)
        for k, v in h.items():
            company[k] = v
        applied = {**applied, **h}

    company["_enrichment_status"] = "gemini_ok_filled_some" if applied else "gemini_ok_nothing_to_add"
    company["_enriched_keys"] = sorted(list(applied.keys()))
    return company


def _extract_gemini_payload(data: dict) -> Any:
    """
    Extract JSON from:
      - content.parts[].functionCall.args (preferred)
      - content.parts[].inlineData/inline_data (base64 JSON)
      - content.parts[].text (JSON string)
    """
    pf = data.get("promptFeedback") or {}
    if pf.get("blockReason"):
        print(f"[GEMINI] blocked: {pf.get('blockReason')}")
        return {}

    cands = data.get("candidates") or []
    for cand in cands:
        content = cand.get("content") or {}
        parts = content.get("parts") or []
        # functionCall path
        for p in parts:
            fc = p.get("functionCall")
            if isinstance(fc, dict):
                args = fc.get("args")
                if isinstance(args, dict):
                    return args
                if isinstance(args, str):
                    try: return json.loads(args)
                    except: pass
        # inlineData path
        for p in parts:
            inline = p.get("inlineData") or p.get("inline_data")
            if isinstance(inline, dict):
                b64 = inline.get("data")
                if isinstance(b64, str) and b64:
                    try:
                        raw = base64.b64decode(b64)
                        return json.loads(raw.decode("utf-8","ignore"))
                    except: pass
        # text path
        texts = [p.get("text") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str)]
        for t in texts:
            t = t.strip()
            if not t: continue
            # extract JSON object
            m = re.search(r"\{.*\}$", t, flags=re.S)
            if m:
                frag = m.group(0)
                try: return json.loads(frag)
                except: pass
    return {}

# ==============================
# Main
# ==============================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sic", required=True, help="SIC code to search (e.g., 7372)")
    ap.add_argument("--companies", type=int, default=3, help="How many similar startups to return (default: 3)")
    ap.add_argument("--scan", type=int, default=60, help="How many CIKs to scan (default: 60)")
    args = ap.parse_args()

    ciks = get_ciks_by_sic(args.sic, max_companies=args.scan)
    if not ciks:
        print(f"No CIKs found for SIC {args.sic}")
        return

    print(f"Discovered {len(ciks)} CIKs for SIC {args.sic}. Scanning for most recent Form D…")

    candidates: List[Dict[str,Any]] = []
    for cik in ciks:
        try:
            meta = recent_form_d(cik)
            if not meta:
                continue
            raw = fetch_form_d_text(cik, meta)
            prof = parse_form_d(raw)
            prof["cik"] = f"{cik}"
            prof["_filing_date"] = meta["date"]
            candidates.append(prof)
            # be gentle with SEC
            time.sleep(0.25 + random.uniform(0,0.2))
        except Exception as e:
            # Just skip problematic issuers
            # print(f"[WARN] CIK {cik}: {e}")
            continue

    if not candidates:
        print("No Form D candidates found.")
        return

    chosen = choose_3_similar(candidates)[:args.companies]
    print(f"Selected {len(chosen)} similar startups.")

    # Enrich via Gemini (one call per company, function-calling)
    out = []
    for i, comp in enumerate(chosen, 1):
        print(f"  - Enriching {i}/{len(chosen)}: {comp.get('company_name') or comp.get('cik')}")
        enriched = gemini_fill_soft(comp)
        out.append(enriched)
        time.sleep(random.uniform(*ENRICH_SLEEP_S))

    print("\n=== 3 Similar Startups (Enriched) ===")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
