import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.limits import WindowLimiter, ProviderAllowanceExceeded, reserve_provider_call
from backend.sample_records import sample_members
from backend.operations import build_worklist


def test_allowance_resets_at_window_boundary():
    now = [59]
    limiter = WindowLimiter(clock=lambda: now[0])
    assert limiter.allow('chat', 1, 60) == (True, 0)
    assert limiter.allow('chat', 1, 60) == (False, 1)
    now[0] = 60
    assert limiter.allow('chat', 1, 60) == (True, 0)
    assert limiter.allow('uploads', 0, 60)[0] is False


def test_daily_provider_cap_and_day_reset(monkeypatch):
    now = [0]
    monkeypatch.setattr('backend.limits.provider_allowance', WindowLimiter(clock=lambda: now[0]))
    monkeypatch.setenv('OPENAI_DAILY_CALL_LIMIT', '1')
    reserve_provider_call()
    with pytest.raises(ProviderAllowanceExceeded):
        reserve_provider_call()
    now[0] = 86400
    reserve_provider_call()


def test_rate_limited_chat_leaves_health_available(monkeypatch):
    monkeypatch.setenv('LANGSMITH_TRACING', 'false')
    monkeypatch.setenv('CHAT_REQUESTS_PER_MINUTE', '0')
    with TestClient(app) as client:
        response = client.post('/chat', json={'question': 'What is my deductible?'})
        assert response.status_code == 429
        assert int(response.headers['Retry-After']) > 0
        assert client.get('/health').status_code == 200


def test_provider_cap_returns_document_evidence_without_paid_call(monkeypatch):
    from backend.workflow import run_workflow
    monkeypatch.setenv('LANGSMITH_TRACING', 'false')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-key')
    monkeypatch.setenv('OPENAI_DAILY_CALL_LIMIT', '0')
    result = run_workflow({'mode': 'document', 'question': 'What is the deductible?',
        'document': {'filename': 'sample.pdf', 'pages': [{'page_number': 1, 'text': 'The annual deductible is $900.'}]}})
    assert result['answer_mode'] == 'extractive_fallback'
    assert result['found'] is True and '$900' in result['answer']
    assert 'daily AI request allowance' in result['notice']


def test_fresh_installation_has_project_owned_service_examples():
    members = sample_members()
    assert len(members) == 12
    assert all(key.startswith('SYN-') and 'GoMask' not in member['source'] for key, member in members.items())
    summary = build_worklist(members)['summary']
    assert summary == dict(transactions=12, patients=12, recorded_exceptions=4, authorization_flags=4, needs_review=5)
