from fastapi.testclient import TestClient
from backend.main import app
from backend.operations import build_worklist


def member(patient='P1', transaction='T1', status='active', response='approved', auth='false'):
    return {'plan': {'eligibility_record': dict(patient_id=patient, transaction_id=transaction,
        coverage_status=status, response_code=response, prior_authorization_required=auth,
        service_type_description='Synthetic service', coverage_type='medical',
        transaction_datetime='2024-01-01T12:00:00')}}


def test_worklist_counts_flags_without_double_counting_transactions():
    data = build_worklist({'a': member(), 'b': member('P2', 'T2', 'pending', 'pending', 'true'),
                          'c': member('P3', 'T3', 'active', 'approved', 'true'),
                          'd': member('P1', 'T4', 'terminated', 'denied')})
    assert data['summary'] == dict(transactions=4, patients=3, recorded_exceptions=2,
                                    authorization_flags=2, needs_review=3)
    assert [r['review_group'] for r in data['records']] == ['exception', 'exception', 'authorization', 'recorded_active']
    pending = data['records'][0]
    assert len(pending['checks']) == 3
    assert all(check['evidence'] and check['action'] for check in pending['checks'])
    assert all('fresh payer check' in row['freshness_note'] for row in data['records'])


def test_active_status_does_not_hide_failed_response():
    row = build_worklist({'a': member(response='error')})['records'][0]
    assert row['review_group'] == 'exception'
    assert row['checks'][0]['evidence'] == 'response_code = error'


def test_builtin_members_are_not_fabricated_as_eligibility_transactions():
    data = build_worklist({'DEMO001': {'plan': {'status': 'fictional'}}})
    assert data['records'] == []
    assert not any(data['summary'].values())


def test_operations_api_and_sample_document():
    with TestClient(app) as client:
        response = client.get('/operations')
        assert response.status_code == 200
        assert response.headers['Cache-Control'] == 'no-store'
        assert response.json()['is_demo'] is True
        assert 'not coverage decisions' in response.json()['notice']
        response = client.get('/synthetic-benefits.pdf')
        assert response.status_code == 200 and response.content.startswith(b'%PDF')
