"""Small, explicit language helpers; never infer missing record values."""
import re


DEFINITIONS = {
    'deductible': 'A deductible is the amount a plan requires you to pay for applicable services before certain benefits begin. Some services may have different rules.',
    'copay': 'A copay is a fixed amount recorded for a service. It does not by itself establish your final bill.',
    'coinsurance': 'Coinsurance is a percentage share of an applicable allowed amount. A percentage alone is not enough to calculate a bill.',
    'authorization': 'Prior authorization is a payer review requirement for a service. A requirement flag does not show that authorization was obtained or that payment is guaranteed.',
}


def normalize_question(question):
    q = question.lower().replace('\u2019', "'")
    for pattern, replacement in (
        (r'\bco[ -]?pay(?:ment)?s?\b', 'copay'),
        (r'\bco[ -]?insurance\b', 'coinsurance'),
        (r'\bpre[ -]?(?:authorization|authorisation|approval)\b', 'authorization'),
        (r'\bauthorisation\b', 'authorization'),
        (r'\bdeductable\b', 'deductible'),
        (r'\b(?:insurer|insurance company|carrier)\b', 'payer'),
    ):
        q = re.sub(pattern, replacement, q)
    return q


def definition_answer(question):
    q = normalize_question(question)
    if not any(phrase in q for phrase in ('what is a ', 'what is an ', 'what does ', 'define ', 'explain ', 'difference between', 'mean')):
        return None
    topics = [key for key in DEFINITIONS if key in q]
    # "Explain my deductible" should still look up the selected record.
    if re.search(r'\b(my|this|recorded|remaining)\b', q):
        return None
    return '\n\n'.join(DEFINITIONS[key] for key in topics) or None


def resolve_followup(question, previous_question=''):
    q = normalize_question(question)
    previous = normalize_question(previous_question)
    if any(term in q for term in ('left', 'remaining', 'balance', 'how much more')) and 'deductible' not in q:
        if 'deductible' in previous:
            return 'What is the remaining deductible?'
    if q.strip(' ?.!') in ('and the copay', 'what about copay', 'and copay'):
        return 'What is the copay?'
    return question
