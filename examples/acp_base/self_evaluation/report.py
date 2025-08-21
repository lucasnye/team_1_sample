import google.generativeai as genai
from dotenv import load_dotenv
import os
import json 

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


model = genai.GenerativeModel(model_name = "gemini-2.5-flash", system_instruction=os.getenv("SYSTEM_INSTRUCTIONS"))

def build_prompt(startup_data: dict, context_data: dict) -> str:
    """
    Build a structured prompt for profitability narrative generation.
    """
    startup_json = json.dumps(startup_data, indent=2)
    context_json = json.dumps(context_data, indent=2)

    prompt = f"""
You are an experienced startup analyst.
Generate a profitability assessment report using ONLY the provided data.
Do not invent numbers. If information is missing, describe qualitative factors instead.

Startup data:
{startup_json}

Context data (similar companies, industry trends):
{context_json}

Write the report in this structure:
1. Executive Summary
2. Industry Context
3. Peer Benchmarking
4. Profitability Outlook (qualitative if numeric data missing)
5. Key Risks and Recommendations
"""
    return prompt.strip()


def generate_report(startup_data: dict, context_data: dict) -> str:
    """
    Generate a profitability narrative using Gemini 2.5 Flash.
    """
    prompt = build_prompt(startup_data, context_data)
    response = model.generate_content(prompt)
    return response.text.strip() if response.text else "(No response returned)"

# Example usage
if __name__ == "__main__":
    startup = {
        "company_name": "IntakeAI",
        "industry": "HealthTech",
        "subsector": "Clinical Workflow Automation",
        "stage": "Seed",
        "hq_location": "San Francisco, CA",
        "business_model": "B2B SaaS",
        "markets": ["North America", "Europe"],
        "moat": "Proprietary patient-intake NLP models",
        "go_to_market": "Direct sales to mid-sized clinics",
        "tech_stack": ["Python", "TensorFlow", "PostgreSQL"],
        "description": "AI-powered intake system that automates patient onboarding and pre-diagnosis questionnaires.",
        "keywords": ["healthcare AI", "automation", "clinical SaaS"],
        "deck_url": "https://example.com/intakeai-deck",
        "website": "https://intakeai.com"
    }

    context = {
    "peer_companies": [
        {
            "company_name": "MedFlow",
            "industry": "HealthTech",
            "subsector": "Clinic Management",
            "stage": "Series A",
            "hq_location": "Boston, MA",
            "business_model": "B2B SaaS",
            "markets": ["North America"],
            "moat": "Exclusive partnerships with major EHR providers",
            "go_to_market": "Channel partners and medical distributors",
            "tech_stack": ["Java", "React", "MongoDB"],
            "description": "End-to-end clinic management suite with integrated billing.",
            "keywords": ["clinic SaaS", "EHR", "workflow"],
            "profitability": "not yet profitable",
            "growth_rate": 0.25
        },
        {
            "company_name": "ClinicAI",
            "industry": "HealthTech",
            "subsector": "Patient Engagement",
            "stage": "Series B",
            "hq_location": "New York, NY",
            "business_model": "B2B SaaS",
            "markets": ["North America", "Asia"],
            "moat": "First-mover advantage with regulatory certifications",
            "go_to_market": "Hybrid inbound and outbound sales",
            "description": "Automated patient follow-up and appointment scheduling.",
            "keywords": ["patient engagement", "automation", "health SaaS"],
            "profitability": "break-even",
            "growth_rate": 0.3
        }
    ]
    }

    report = generate_report(startup, context)
    print("=== Profitability Report ===")
    print(report)