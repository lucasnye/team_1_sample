import os, json, time
from dotenv import load_dotenv
import google.generativeai as genai
from jsonschema import validate, ValidationError

load_dotenv()
genai.configure(api_key="AIzaSyC-hhgehvJvVnyTcxpaWMQUUGUOi_xwlIc")

PROPOSAL_SCHEMA = {
    "type": "object",
    "required": ["company_name","industry","stage","description"],
    "properties": {
        "company_name": {"type": "string"},
        "industry": {"type": "string"},
        "subsector": {"type": "string"},
        "stage": {"type": "string"},
        "hq_location": {"type": "string"},
        "business_model": {"type": "string"},
        "markets": {"type": "array", "items": {"type": "string"}},
        "moat": {"type": "string"},
        "go_to_market": {"type": "string"},
        "tech_stack": {"type": "array", "items": {"type": "string"}},
        "description": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "deck_url": {"type": "string"},
        "website": {"type": "string"}        
    }
}

GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.9,
    "max_output_tokens": 2048,
    "response_mime_type": "application/json",
    "response_schema": PROPOSAL_SCHEMA,
}

SYSTEM_INSTRUCTIONS = (
    "Extract structured data about a startup from messy text. "
    "Return STRICT JSON that matches the provided JSON Schema. "
    "If a field is missing/unclear, set it to null or an empty array. "
    "Don't invent facts. Only include fields defined by the schema."
)

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", 
    system_instruction=SYSTEM_INSTRUCTIONS,
)

def parse_proposal(long_string: str, max_retries: int = 2):
    errors_to_model = ""
    for attempt in range(max_retries + 1):
        contents = f"""JSON_SCHEMA:
{json.dumps(PROPOSAL_SCHEMA)}

TEXT_TO_PARSE:
{long_string}

{('VALIDATION_ERRORS_FROM_PREVIOUS_ATTEMPT:\n' + errors_to_model) if errors_to_model else ''}"""

        resp = model.generate_content(
            contents,
            generation_config=GENERATION_CONFIG,
        )

        raw = resp.text
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            errors_to_model = f"Model returned non‑JSON: {e}. Raw: {raw[:3000]}"
            time.sleep(0.5)
            continue

        try:
            validate(instance=data, schema=PROPOSAL_SCHEMA)
            return data
        except ValidationError as ve:
            errors_to_model = f"{ve.message}; at path: {'/'.join(map(str, ve.path))}"
            time.sleep(0.5)

    raise RuntimeError(f"Failed to produce valid JSON after retries. Last error: {errors_to_model}")