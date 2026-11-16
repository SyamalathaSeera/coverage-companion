"""Explainable review worklist for synthetic historical eligibility records."""
from backend.gomask import SOURCE, SOURCE_URL


def review_record(member_id, record):
    checks = []
    if record['coverage_status'] != 'active':
        checks.append(dict(code='coverage_exception', label='Coverage status needs review',
                           evidence=f"coverage_status = {record['coverage_status']}",
                           action='Ask the payer to confirm coverage dates and status for the intended service date.'))
    if record['response_code'] != 'approved':
        checks.append(dict(code='response_exception', label='Eligibility response needs review',
                           evidence=f"response_code = {record['response_code']}",
                           action='Review the response with the payer; resolve the eligibility transaction before relying on it.'))
    if record['prior_authorization_required'] == 'true':
        checks.append(dict(code='authorization', label='Authorization requirement recorded',
                           evidence='prior_authorization_required = true',
                           action='Confirm the service-specific authorization requirement and obtain its status from the payer.'))
    exceptions = any(c['code'] != 'authorization' for c in checks)
    return dict(member_id=member_id, patient_id=record['patient_id'], transaction_id=record['transaction_id'],
                service=record['service_type_description'], coverage_type=record['coverage_type'],
                recorded_status=record['coverage_status'], response_code=record['response_code'],
                recorded_at=record['transaction_datetime'], checks=checks,
                review_group='exception' if exceptions else 'authorization' if checks else 'recorded_active',
                review_label='Recorded exception' if exceptions else 'Authorization flagged' if checks else 'Recorded active',
                next_step='; '.join(dict.fromkeys(c['action'] for c in checks)) if checks else
                    'Recheck eligibility for the intended service date, then review the recorded service benefits.',
                freshness_note='Historical synthetic transaction. Every record needs a fresh payer check before real use.',
                source=SOURCE, source_url=SOURCE_URL)


def build_worklist(members):
    records = [{**review_record(key, member['plan']['eligibility_record']),
                'source': member.get('source', SOURCE), 'source_url': member.get('source_url', SOURCE_URL)} for key, member in members.items()
               if 'eligibility_record' in member['plan']]
    order = {'exception': 0, 'authorization': 1, 'recorded_active': 2}
    records.sort(key=lambda r: (order[r['review_group']], r['transaction_id']))
    return dict(is_demo=True, records=records, summary=dict(
        transactions=len(records), patients=len({r['patient_id'] for r in records}),
        recorded_exceptions=sum(r['review_group'] == 'exception' for r in records),
        authorization_flags=sum(any(c['code'] == 'authorization' for c in r['checks']) for r in records),
        needs_review=sum(bool(r['checks']) for r in records)),
        notice='Historical synthetic data only. Review flags are workflow prompts, not coverage decisions or predicted claim denials.')
