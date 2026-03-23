"""
Auto-update knowledge base with latest CBDT circulars and tax news.
Called by GitHub Actions weekly, or manually.
Uses Gemini API to summarize new developments into KB entries.
"""
import requests, json, os, re
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
KB_PATH = "knowledge_base.py"

def call_gemini(prompt):
    """Simple Gemini call for summarization"""
    if not GEMINI_API_KEY:
        print("No GEMINI_API_KEY set. Skipping AI summarization.")
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2000}
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini error: {e}")
    return None

def search_latest_tax_news():
    """Use Gemini with grounding to find latest CBDT circulars"""
    prompt = """You are a tax research assistant. List the 3 most important Indian income tax developments 
    from the LAST 2 WEEKS (CBDT circulars, notifications, ITAT rulings, or tax law changes).
    
    For each, provide:
    - Date (YYYY-MM-DD)
    - Title (brief)
    - Section of IT Act affected
    - Category (one of: legislation, compliance, deductions, exemptions, capital_gains, trading, nri, tds, case_law)
    - Summary (2-3 sentences, factual, citing specific section numbers)
    - Source (circular number or case citation)
    
    Format as JSON array. Only include items you are CERTAIN about. If nothing significant happened, return empty array [].
    """
    result = call_gemini(prompt)
    if not result:
        return []
    # Try to parse JSON from response
    try:
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'\[.*\]', result, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    return []

def read_existing_ids():
    """Read existing KB entry IDs to avoid duplicates"""
    ids = set()
    with open(KB_PATH, 'r') as f:
        content = f.read()
    for match in re.finditer(r'"id"\s*:\s*"([^"]+)"', content):
        ids.add(match.group(1))
    return ids

def add_entry_to_kb(entry):
    """Add a new entry to the knowledge_base.py file"""
    with open(KB_PATH, 'r') as f:
        content = f.read()
    
    # Find the closing ] of TAX_KNOWLEDGE_BASE
    lines = content.split('\n')
    insert_at = None
    for i, line in enumerate(lines):
        if 'def search_knowledge' in line:
            for j in range(i-1, 0, -1):
                if lines[j].strip() == ']':
                    insert_at = j
                    break
            break
    
    if insert_at is None:
        print("Could not find insertion point in KB")
        return False
    
    # Format the new entry
    new_entry = f'    {json.dumps(entry, ensure_ascii=False)},'
    lines.insert(insert_at, new_entry)
    
    with open(KB_PATH, 'w') as f:
        f.write('\n'.join(lines))
    return True

def main():
    print(f"TaxGuru KB Auto-Update — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    existing_ids = read_existing_ids()
    print(f"Existing KB entries: {len(existing_ids)}")
    
    news = search_latest_tax_news()
    print(f"Found {len(news)} potential updates")
    
    added = 0
    for item in news:
        # Generate a unique ID
        title = item.get('title', '')
        date = item.get('date', datetime.now().strftime('%Y-%m-%d'))
        entry_id = f"auto_{date}_{re.sub(r'[^a-z0-9]', '_', title.lower()[:30])}"
        
        if entry_id in existing_ids:
            print(f"  Skip (exists): {title}")
            continue
        
        entry = {
            "id": entry_id,
            "section": item.get('section', 'General'),
            "category": item.get('category', 'legislation'),
            "applies_to": ["all"],
            "title": title,
            "content": item.get('summary', ''),
            "last_updated": date,
            "source": item.get('source', 'Auto-detected')
        }
        
        if add_entry_to_kb(entry):
            print(f"  Added: {title}")
            added += 1
    
    print(f"Done. Added {added} new entries.")

if __name__ == "__main__":
    main()
