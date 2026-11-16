import json
from pathlib import Path
from fastapi import HTTPException
from backend.gomask import as_members, create_record_answer
from backend.sample_records import sample_members
from backend.questions import normalize_question, definition_answer

MEMBERS = json.loads((Path(__file__).parent / 'data' / 'members.json').read_text(encoding='utf-8'))
MEMBERS.update(sample_members())
gomask_file = Path(__file__).parent / 'data' / 'gomask.json'
if gomask_file.exists():
    MEMBERS.update(as_members(json.loads(gomask_file.read_text(encoding='utf-8'))))


def find_member(member_id):
    member_id = member_id.strip().upper()
    if member_id not in MEMBERS:
        raise HTTPException(404, 'Sample member not found. Choose a record from the member selector.')
    return member_id, MEMBERS[member_id]


def create_answer(question, plan):
    if 'eligibility_record' in plan:
        return create_record_answer(question, plan['eligibility_record'])
    q = normalize_question(question)
    definition = definition_answer(question)
    if definition:
        return definition + ' General explanation only; this is not a coverage determination.'
    unsupported = 'The fictional records only contain plan name, annual deductible, primary care copay, and mock coverage status. They contain no claims or other benefit details.'
    if any(term in q for term in ('specialist', 'dental', 'vision', 'surgery', 'emergency', 'prescription', 'claim', 'remaining', 'out-of-pocket', 'hospital', 'therapy', 'family')):
        return unsupported
    answers = []
    summary = any(term in q for term in ('summary', 'summarize', 'overview', 'tell me about'))
    if 'deductible' in q or summary:
        answers.append(f"The annual deductible is ${plan['annual_deductible']:,} (not a remaining balance).")
    if 'copay' in q or summary:
        answers.append(f"The primary care copay is ${plan['primary_care_copay']}.")
    if summary or any(word in q for word in ('active', 'status', 'eligib', 'coverage')):
        answers.append(f"Mock eligibility: {plan['status']}. No insurer was contacted.")
    if summary or (not answers and ('plan' in q or 'insurance' in q)):
        answers.append(f"The fictional plan is {plan['name']}.")
    if 'provider' in q or 'payer' in q:
        answers.append('Provider and payer identifiers or names are not supplied in this basic demo record. Select a service record to inspect its recorded IDs.')
    if q.strip(' ?.!') in ('hi', 'hello', 'hey', 'help', 'what can you do'):
        answers.append('Ask me to summarize this plan, show its deductible or primary care copay, check its mock status, or explain deductible, copay, coinsurance, and authorization. Select a service record for more detailed examples.')
    if not answers:
        return unsupported
    return ' '.join(answers) + ' Fictional demo data; this does not establish current eligibility or guarantee payment.'
