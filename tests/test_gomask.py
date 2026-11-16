import copy
import pytest
from fastapi.testclient import TestClient
from backend.gomask import as_members, normalize_records, create_record_answer
from backend.main import app
from backend.members import MEMBERS


@pytest.fixture
def record():
    return dict(transaction_id='TEST001', patient_id='PATTEST', payer_id='PAYER', provider_id='PROVIDER',
                coverage_status='active', coverage_type='dental', coverage_effective_date='2023-01-01',
                coverage_end_date='', deductible_met_amount='60.50', deductible_total_amount='200',
                copay_amount='45', coinsurance_percentage='15', prior_authorization_required='false',
                benefit_limit_type='visit', benefit_limit_value='8', service_type_code='35',
                service_type_description='Routine Dental', transaction_datetime='2024-02-21T14:20:00',
                response_code='approved', response_message='Synthetic fixture')


def test_same_patient_distinct_transactions(record):
    second = {**record, 'transaction_id': 'TEST002', 'copay_amount': '60'}
    members = as_members([record, second])
    assert len(members) == 2
    assert members['GM-TEST001']['plan']['eligibility_record']['copay_amount'] == '45'
    assert members['GM-TEST002']['plan']['eligibility_record']['copay_amount'] == '60'
    with pytest.raises(ValueError, match='duplicate'):
        normalize_records([record, copy.deepcopy(record)])


@pytest.mark.parametrize('field,value', [('copay_amount', 'NaN'), ('copay_amount', '-1'),
    ('coinsurance_percentage', '101'), ('transaction_id', '<script>'),
    ('prior_authorization_required', 'maybe')])
def test_invalid_export(record, field, value):
    record[field] = value
    with pytest.raises(ValueError):
        normalize_records([record])


def test_missing_columns(record):
    del record['deductible_total_amount']
    with pytest.raises(ValueError, match='20 GoMask columns'):
        normalize_records([record])


def test_service_scope_and_historical_status(record):
    answer = create_record_answer('What is my dental copay?', record)
    assert '$45.00' in answer and 'Routine Dental' in answer
    assert '2024-02-21' in answer and 'not current eligibility' in answer
    for question in ('What is my primary care copay?', 'What is my prescription copay?', 'Are implants covered?'):
        assert 'does not establish' in create_record_answer(question, record)
        assert '$45.00' not in create_record_answer(question, record)
    record.update(coverage_status='terminated', response_code='denied', copay_amount='0')
    answer = create_record_answer('What is my copay?', record)
    assert 'not an approved active' in answer and 'zero does not establish free coverage' in answer


def test_deductible_does_not_assume_annual(record):
    answer = create_record_answer('What is my remaining deductible?', record)
    assert '$139.50' in answer and 'not a live balance' in answer
    assert 'annual' not in answer


@pytest.mark.parametrize('provider_id', ['PROVIDER', ''])
def test_provider_question_reports_only_available_identity(record, provider_id):
    record['provider_id'] = provider_id
    answer = create_record_answer('Who is my provider?', record)
    assert f"Recorded provider ID: {provider_id or 'not supplied'}." in answer
    assert 'Provider name is not supplied.' in answer
    assert 'does not establish the requested benefit' not in answer
    assert 'not current eligibility' in answer


def test_api_lists_and_answers_imported_records(record, monkeypatch):
    monkeypatch.setitem(MEMBERS, 'GM-TEST001', as_members([record])['GM-TEST001'])
    with TestClient(app) as client:
        members = client.get('/members').json()['members']
        assert any(m['member_id'] == 'GM-TEST001' for m in members)
        plan = client.get('/plan?member_id=GM-TEST001').json()
        assert plan['source'].startswith('GoMask')
        answer = client.post('/chat', json={'member_id': 'gm-test001', 'question': 'What is my copay?'}).json()
        assert answer['source'].startswith('GoMask')
        assert '$45.00' in answer['answer']
        assert answer['answer_mode'] == 'deterministic'


def test_sequential_questions_return_distinct_answers(record, monkeypatch):
    monkeypatch.setitem(MEMBERS, 'GM-TEST001', as_members([record])['GM-TEST001'])
    with TestClient(app) as client:
        answers = [client.post('/chat', json={'member_id': 'GM-TEST001', 'question': question}).json()['answer']
                   for question in ('Who is my provider?', 'What is the deductible?', 'What is the copay?')]
    assert answers[0].startswith('Recorded provider ID: PROVIDER.')
    assert answers[1].startswith('Recorded deductible total: $200.00; met: $60.50.')
    assert answers[2].startswith('Recorded service copay: $45.00.')
    assert len(set(answers)) == 3
    assert '$45.00' not in answers[1]
    assert '$200.00' not in answers[2]
