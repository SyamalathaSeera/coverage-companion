"""Conversation scenarios for broader record questions and honest limits."""
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.members import MEMBERS
from backend.sample_records import sample_members


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('LANGSMITH_TRACING', 'false')
    for key, member in sample_members().items():
        monkeypatch.setitem(MEMBERS, key, member)
    with TestClient(app) as client:
        yield client


def ask(client, question, member='SYN-SAMPLE002', **extra):
    response = client.post('/chat', json=dict(member_id=member, question=question, **extra))
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize('question,expected', [
    ('What is my co payment?', '$35.00'),
    ('What is my deductable?', '$180.00'),
    ('How much of my deductible is left?', '$140.00'),
    ('Who is my insurance company?', 'Recorded payer ID: SAMPLE-PAYER'),
    ('Do I need pre-approval?', 'not required'),
    ('When does coverage start?', '2024-01-01'),
    ('Show the recorded cost breakdown', 'cannot be added together'),
    ('What should I check next?', 'Recheck eligibility'),
])
def test_common_phrasing(client, question, expected):
    assert expected in ask(client, question)['display_answer']


def test_summary_and_context_are_separate(client):
    data = ask(client, 'Summarize this record')
    assert all(value in data['display_answer'] for value in ('$180.00', '$40.00', '$35.00', 'SYN002'))
    assert 'Synthetic historical record' in data['record_context']


def test_followup_uses_explicit_context_without_cross_request_memory(client):
    assert '$140.00' in ask(client, 'How much is left?', previous_question='What is my deductible?')['answer']
    assert '$140.00' not in ask(client, 'How much is left?')['answer']
    assert '$750.00' in ask(client, 'How much is left?', member='SYN-SAMPLE009', previous_question='deductible')['answer']


def test_definitions_dont_become_record_claims(client):
    data = ask(client, 'Explain the difference between copay and coinsurance')
    assert 'fixed amount' in data['display_answer'] and 'percentage' in data['display_answer']
    assert '$35.00' not in data['answer']


def test_new_services_and_authorization_limitations(client):
    assert '$60.00' in ask(client, 'What is the urgent care copay?', 'SYN-SAMPLE009')['answer']
    imaging = ask(client, 'Does imaging require pre-approval?', 'SYN-SAMPLE010')['answer']
    assert 'recorded as required' in imaging and 'does not include authorization approval' in imaging
    therapy = ask(client, 'What is my therapy benefit limit?', 'SYN-SAMPLE011')['answer']
    assert '12 (type: visits)' in therapy
    lab = ask(client, 'What is the laboratory copay?', 'SYN-SAMPLE012')['answer']
    assert '$0.00' in lab and 'zero does not establish free coverage' in lab


def test_unsupported_service_and_unknown_question_offer_help(client):
    for question in ('What is my emergency copay?', 'Can I book an appointment?', 'What is my network?', 'something unknown'):
        data = ask(client, question)
        assert 'does not establish the requested benefit' in data['display_answer']
        assert '$35.00' not in data['display_answer']
        assert 'Summarize this record' in data['display_answer']


def test_pending_response_explanation_does_not_invent_reason(client):
    data = ask(client, 'Why is this pending?', 'SYN-SAMPLE011')
    assert 'pending' in data['display_answer']
    assert 'No additional reason is established' in data['display_answer']
    assert 'obtain its status from the payer' in data['display_answer']


def test_document_paraphrases_preserve_sources_and_unsupported_terms():
    from backend.retrieval import retrieve
    document = dict(filename='example.pdf', pages=[dict(page_number=3, text='The primary care copay is $25. The deductible is $1,000.')])
    for question in ('Could you tell me the primary care co-payment?', 'Can you show my deductable?'):
        result = retrieve(question, document)
        assert result and result[0]['page_number'] == 3
        assert result[0]['excerpt'] in document['pages'][0]['text']
    assert not retrieve('What is the remaining deductible?', document)
    assert not retrieve('What is the dental implant copay?', document)
