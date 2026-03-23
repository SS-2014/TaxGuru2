"""
TaxGuru — Gemini API Integration with RAG
Handles: LLM calls, RAG context injection, privacy filtering, multi-language chat
"""

import json
import re
import os
import hashlib
from typing import Optional

# ── Privacy Layer ──

SENSITIVE_PATTERNS = {
    'pan': r'\b[A-Z]{5}\d{4}[A-Z]\b',
    'aadhaar': r'\b\d{4}\s?\d{4}\s?\d{4}\b',
    'bank_account': r'\b\d{9,18}\b',
    'ifsc': r'\b[A-Z]{4}0[A-Z0-9]{6}\b',
    'phone': r'\b[+]?91[-\s]?\d{10}\b|\b\d{10}\b',
    'email': r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
    'date_of_birth': r'\b\d{2}[/-]\d{2}[/-]\d{4}\b',
    'pf_number': r'\b[A-Z]{2}[/]?[A-Z]{3}[/]?\d{7}[/]?\d{3}[/]?\d{7}\b',
    'uan': r'\b\d{12}\b',  # Universal Account Number
}


def anonymize_text(text: str) -> tuple:
    """Remove all PII from text, return (clean_text, redacted_items_count)"""
    redacted_count = 0
    clean = text
    for pii_type, pattern in SENSITIVE_PATTERNS.items():
        matches = re.findall(pattern, clean)
        for match in matches:
            clean = clean.replace(match, f'[REDACTED_{pii_type.upper()}]')
            redacted_count += 1
    return clean, redacted_count


def generate_anonymous_id(user_data: dict) -> str:
    """Generate a consistent anonymous user ID from non-sensitive profile data"""
    key_data = f"{user_data.get('taxpayer_type', '')}-{user_data.get('age', '')}-{user_data.get('income_bracket', '')}"
    return hashlib.sha256(key_data.encode()).hexdigest()[:12]


def extract_financial_only(profile: dict) -> dict:
    """Extract only financial figures, stripping all PII"""
    safe_fields = [
        'taxpayer_type', 'age', 'residency', 'gross_salary', 'basic_salary',
        'hra_received', 'business_income', 'professional_income', 'trading_income',
        'rental_income', 'interest_income', 'dividend_income',
        'stcg_equity', 'ltcg_equity', 'stcg_other', 'ltcg_other',
        'esop_perquisite', 'esop_sale_gain', 'foreign_esop',
        'section_80c', 'section_80d_self', 'section_80d_parents',
        'section_80e', 'section_80g', 'section_80ccd_1b', 'section_80ccd_2',
        'section_24b', 'rent_paid_annual', 'metro_city',
        'tds_deducted', 'advance_tax_paid',
    ]
    return {k: v for k, v in profile.items() if k in safe_fields}


# ── System Prompts ──

SYSTEM_PROMPT_TAX_ADVISOR = """You are {agent_name}, a personal Indian income tax advisor on the TaxGuru platform, for FY 2025-26 (AY 2026-27).

CORE PRINCIPLES:
1. ACCURACY FIRST: Only provide advice grounded in the Income Tax Act (1961 and 2025), Finance Acts, CBDT circulars, and established case law. If you are unsure, say so clearly.
2. NO HALLUCINATION: Never invent tax sections, rates, or rules. If you don't know something, say "I'm not certain — please consult a Chartered Accountant for this specific question."
3. CITE SECTIONS: Always reference the specific section/rule (e.g., "Under Section 80C...", "As per Section 112A...").
4. REGIME AWARENESS: Always clarify whether a deduction/exemption applies to Old Regime, New Regime, or both.
5. TONE: Professional, warm, helpful. Speak as {agent_name}. Use first person ("I recommend...", "Based on your numbers, I see that..."). Not robotic or overly formal.
6. PRIVACY: Never ask for PAN, Aadhaar, bank account numbers, or personal identifiers. Only work with financial figures.
7. REAL-TIME: You have access to provisions up to the CBDT notification of Income Tax Rules 2026 (March 20, 2026). The new Income Tax Act 2025 takes effect from April 2026. HRA now covers 8 metro cities. CARF (Crypto Asset Reporting) is now in effect.
8. MULTILINGUAL: When responding in Hindi, Tamil, Telugu, or Kannada, keep tax terminology in English in parentheses for clarity. Refer to yourself as {agent_name} in all languages.

When answering:
- Start with the direct answer to the user's question
- Cite the relevant section/rule
- Give actionable next steps
- If the situation is complex, recommend consulting a CA
- If asked about very recent developments, note what you know and suggest checking incometaxindia.gov.in for the latest"""

SYSTEM_PROMPT_DOCUMENT_ANALYZER = """You are a document analysis agent for TaxGuru. You extract financial data from Indian payslips, Form 16, and employer tax statements.

DOCUMENT TYPES YOU HANDLE:
1. PAYSLIP (monthly): Contains one month's salary breakdown. You must indicate "period": "monthly" so we can annualize.
2. FORM 16 (annual): Issued by employer, contains full-year salary, deductions, and TDS. Indicate "period": "annual".
3. TAX COMPUTATION STATEMENT (annual): Employer's tax projection. Indicate "period": "annual".

EXTRACT these fields (use 0 if not found, "NOT_FOUND" only if the document type should have it but it's illegible):
- gross_salary: Total gross salary/CTC
- basic_salary: Basic pay component
- hra: House Rent Allowance
- special_allowance: Special/flexible allowance
- lta: Leave Travel Allowance
- pf_employee: Employee PF contribution
- pf_employer: Employer PF contribution
- professional_tax: Professional tax deducted
- tds_deducted: Income tax / TDS deducted
- standard_deduction: Standard deduction (usually 50000 or 75000 if shown)
- section_80c_total: Total 80C investments if shown (EPF + PPF + ELSS + LIC etc.)
- section_80d: Health insurance premium if shown
- section_80ccd_1b: NPS employee additional if shown
- section_80ccd_2: NPS employer contribution if shown
- section_24b: Home loan interest if shown
- other_income: Any other income mentioned
- net_taxable_income: Net taxable income if computed in document
- tax_old_regime: Tax under old regime if shown
- tax_new_regime: Tax under new regime if shown
- period: "monthly" or "annual" — CRITICAL, determines if we multiply by 12

RULES:
1. Extract exact numbers. Do not estimate or round.
2. For Form 16: Look for Part B (Annexure) which has detailed salary breakup and deductions.
3. Never extract: Employee name, PAN, bank account, address, employee ID, UAN, PF number, company name, TAN, or any personal identifiers.
4. Return ONLY a valid JSON object. No markdown, no explanation, no backticks."""

LANGUAGE_PROMPTS = {
    'hi': "Respond in Hindi (Devanagari script). Use simple Hindi that is easy to understand. For technical tax terms, use the English term in parentheses. Example: 'कर छूट (Tax Exemption)'. Keep the same accuracy and section references as English responses.",
    'ta': "Respond in Tamil (Tamil script). Use simple Tamil. For technical tax terms, keep the English term in parentheses. Example: 'வரி விலக்கு (Tax Exemption)'. Maintain accuracy and cite sections.",
    'te': "Respond in Telugu (Telugu script). Use simple Telugu. For technical tax terms, keep the English term in parentheses. Maintain accuracy and cite sections.",
    'kn': "Respond in Kannada (Kannada script). Use simple Kannada. For technical tax terms, keep the English term in parentheses. Maintain accuracy and cite sections.",
    'en': "",  # Default English, no additional instruction
}


# ── Gemini API Caller ──

def call_gemini(prompt: str, system_prompt: str = SYSTEM_PROMPT_TAX_ADVISOR,
                context: str = "", language: str = "en",
                api_key: str = None, model: str = "gemini-2.5-flash-lite",
                agent_name: str = "TaxGuru AI") -> str:
    """Call Gemini API with RAG context and language support"""
    import requests

    # Inject agent name into system prompt
    system_prompt = system_prompt.replace("{agent_name}", agent_name)

    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return "Error: Gemini API key not configured. Please set GEMINI_API_KEY."

    # Build the full prompt with RAG context
    full_prompt_parts = [system_prompt]

    if language != 'en' and language in LANGUAGE_PROMPTS:
        full_prompt_parts.append(f"\n\nLANGUAGE INSTRUCTION: {LANGUAGE_PROMPTS[language]}")

    if context:
        full_prompt_parts.append(f"\n\nRELEVANT TAX LAW CONTEXT (use this to ground your answer):\n{context}")

    full_prompt_parts.append(f"\n\nUSER QUERY: {prompt}")

    full_system = "\n".join(full_prompt_parts)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": full_system}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3,  # Low temperature for factual accuracy
            "topP": 0.8,
            "maxOutputTokens": 2048,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if 'candidates' in data and data['candidates']:
                return data['candidates'][0]['content']['parts'][0]['text']
            return "I couldn't generate a response. Please try rephrasing your question."
        elif response.status_code == 429:
            return "I'm currently handling too many requests. Please wait a moment and try again. (API rate limit reached)"
        else:
            return f"Service temporarily unavailable (Error {response.status_code}). Please try again."
    except requests.exceptions.Timeout:
        return "The request took too long. Please try a simpler question or try again."
    except Exception as e:
        return f"An error occurred: {str(e)}"


def analyze_document(image_bytes: bytes, api_key: str, mime_type: str = "image/jpeg") -> dict:
    """Analyze a payslip/Form 16 image using Gemini Vision"""
    import requests
    import base64

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    b64_data = base64.b64encode(image_bytes).decode('utf-8')

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT_DOCUMENT_ANALYZER + "\n\nExtract all financial data from this payslip/Form 16 document. Return ONLY a JSON object with the extracted fields. No personal identifiers."},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": b64_data
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024,
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=45)
        if response.status_code == 200:
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            # Try to parse JSON from response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            return {"raw_text": text, "parse_error": "Could not extract structured data"}
        else:
            return {"error": f"API returned status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}


# ── RAG Query Builder ──

def build_rag_query(user_question: str, taxpayer_profile: dict = None) -> dict:
    """Build a RAG-enhanced query with relevant knowledge base context"""
    from knowledge_base import search_knowledge, format_for_llm_context, get_for_taxpayer_type

    # Determine search terms from user question
    question_lower = user_question.lower()

    # Map question keywords to knowledge base categories
    keyword_map = {
        '80c': 'section_80c', 'elss': 'section_80c', 'ppf': 'section_80c', 'epf': 'section_80c',
        '80d': 'section_80d', 'health insurance': 'section_80d', 'mediclaim': 'section_80d',
        'nps': 'section_80ccd', '80ccd': 'section_80ccd',
        'hra': 'hra_exemption', 'house rent': 'hra_exemption',
        'home loan': 'home_loan', '24b': 'home_loan', 'housing loan': 'home_loan',
        'capital gain': 'capital_gains_equity', 'ltcg': 'capital_gains_equity', 'stcg': 'capital_gains_equity',
        'esop': 'esop_taxation', 'stock option': 'esop_taxation', 'rsu': 'esop_taxation',
        'f&o': 'fno_trading', 'futures': 'fno_trading', 'options': 'fno_trading', 'derivative': 'fno_trading',
        'crypto': 'crypto_taxation', 'bitcoin': 'crypto_taxation', 'virtual digital': 'crypto_taxation',
        'new regime': 'new_regime_slabs', 'old regime': 'old_regime_slabs', 'which regime': 'regime_comparison',
        'slab': 'new_regime_slabs', 'tax rate': 'new_regime_slabs',
        'budget 2026': 'budget_2026', 'new act': 'new_it_act_2025',
        'senior citizen': 'senior_citizen_benefits', 'tds': 'tds_key_provisions',
        'advance tax': 'advance_tax', 'rental': 'rental_income', 'rent income': 'rental_income',
        'education loan': 'section_80e', '80e': 'section_80e',
        'donation': 'section_80g', '80g': 'section_80g',
        'saving': 'section_80tta_80ttb', '80tta': 'section_80tta_80ttb',
        'business income': 'business_income', 'professional income': 'business_income',
        'professional tax': 'professional_tax',
        'surcharge': 'surcharge_cess', 'cess': 'surcharge_cess',
    }

    # Find relevant entries
    relevant_ids = set()
    for keyword, entry_id in keyword_map.items():
        if keyword in question_lower:
            relevant_ids.add(entry_id)

    # If no specific match, provide regime comparison and relevant taxpayer entries
    if not relevant_ids:
        relevant_ids.add('regime_comparison')
        relevant_ids.add('new_regime_slabs')

    # Add taxpayer-type specific entries
    from knowledge_base import TAX_KNOWLEDGE_BASE
    relevant_entries = [e for e in TAX_KNOWLEDGE_BASE if e['id'] in relevant_ids]

    # Also add entries matching the taxpayer type
    if taxpayer_profile and 'taxpayer_type' in taxpayer_profile:
        tt = taxpayer_profile['taxpayer_type']
        type_entries = [e for e in TAX_KNOWLEDGE_BASE
                       if tt in e['applies_to'] and e['id'] not in relevant_ids]
        relevant_entries.extend(type_entries[:2])  # Add max 2 more

    context = format_for_llm_context(relevant_entries, max_entries=5)

    return {
        'context': context,
        'matched_sections': [e['section'] for e in relevant_entries],
        'entry_count': len(relevant_entries),
    }


# ── Feedback System ──

def should_ask_feedback(session_interactions: int, last_feedback_at: int) -> bool:
    """Determine if we should ask for feedback — non-intrusive timing"""
    # Ask after every 5 meaningful interactions, minimum gap of 3 interactions
    if session_interactions < 3:
        return False
    if session_interactions - last_feedback_at < 5:
        return False
    if session_interactions in [5, 15, 30]:  # Specific milestones
        return True
    return False


FEEDBACK_PROMPTS = [
    "Was this tax analysis helpful? A quick rating helps us improve.",
    "How did we do? Your feedback helps TaxGuru get smarter.",
    "Quick check — did this answer your question clearly?",
]
