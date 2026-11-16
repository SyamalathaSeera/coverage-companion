"""Simple lexical retrieval: bounded overlapping passages with original page numbers."""
import re

STOP = set('what is are the a an my me of for in on does do how much about this document plan insurance please tell and to it says say benefits benefit cost costs'.split())
ALIASES = {'co': 'copay', 'copayment': 'copay', 'copayments': 'copay', 'deductibles': 'deductible', 'medicines': 'prescription', 'drugs': 'prescription', 'drug': 'prescription', 'prescriptions': 'prescription'}


def tokens(text):
    return {ALIASES.get(t, t) for t in re.findall(r'[a-z0-9]+', text.lower()) if t not in STOP and len(t) > 1}


def retrieve(question, document):
    query = tokens(question)
    if not query:
        return []
    ranked = []
    for page in document['pages']:
        text = page['text']
        for start in range(0, len(text), 600):
            excerpt = text[start:start + 800]
            overlap = query & tokens(excerpt)
            # Require every meaningful query term. Conservative retrieval favors abstention.
            if overlap != query:
                continue
            ranked.append(dict(document=document['filename'], page_number=page['page_number'], excerpt=excerpt))
    return ranked[:4]
