"""Read synthetic eligibility transactions without inventing plan benefits."""
import re
from decimal import Decimal, InvalidOperation

SOURCE = 'GoMask synthetic Eligibility and Benefits Verification dataset'
SOURCE_URL = 'https://gomask.ai/marketplace/datasets/eligibility-and-benefits-verification'
FIELDS = ('transaction_id patient_id payer_id provider_id coverage_status coverage_type '
          'coverage_effective_date coverage_end_date deductible_met_amount deductible_total_amount '
          'copay_amount coinsurance_percentage prior_authorization_required benefit_limit_type '
          'benefit_limit_value service_type_code service_type_description transaction_datetime '
          'response_code response_message').split()
NUMBERS = ('deductible_met_amount', 'deductible_total_amount', 'copay_amount',
           'coinsurance_percentage', 'benefit_limit_value')


def normalize_records(rows):
    records = []
    seen = set()
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict) or any(field not in row for field in FIELDS):
            raise ValueError(f'Row {index}: expected all 20 GoMask columns.')
        record = {field: str(row[field]).strip() if row[field] is not None else '' for field in FIELDS}
        for field in ('transaction_id', 'patient_id'):
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,27}', record[field]):
                raise ValueError(f'Row {index}: invalid {field}.')
        record['transaction_id'] = record['transaction_id'].upper()
        if record['transaction_id'] in seen:
            raise ValueError(f'Row {index}: duplicate transaction_id.')
        seen.add(record['transaction_id'])
        for field in NUMBERS:
            try:
                value = Decimal(record[field])
            except InvalidOperation:
                raise ValueError(f'Row {index}: invalid {field}.') from None
            if not value.is_finite() or value < 0 or (field == 'coinsurance_percentage' and value > 100):
                raise ValueError(f'Row {index}: invalid {field}.')
        auth = record['prior_authorization_required'].lower()
        if auth not in ('true', 'false', 'yes', 'no'):
            raise ValueError(f'Row {index}: invalid prior_authorization_required.')
        record['prior_authorization_required'] = 'true' if auth in ('true', 'yes') else 'false'
        if record['coverage_end_date'].lower() in ('', 'n/a', 'null', 'none', '\ufffdblank', '\u2014blank'):
            record['coverage_end_date'] = ''
        if any(len(value) > 2000 for value in record.values()):
            raise ValueError(f'Row {index}: field too long.')
        records.append(record)
        if len(records) > 10000:
            raise ValueError('At most 10,000 transactions are supported.')
    if not records:
        raise ValueError('The export contains no records.')
    return records


def as_members(rows):
    return {'GM-' + r['transaction_id']: {
        'member_name': f"{r['patient_id']} / {r['service_type_description']}",
        'source': SOURCE, 'source_url': SOURCE_URL,
        'plan': {'name': 'Plan name not supplied', 'status': r['coverage_status'], 'eligibility_record': r}
    } for r in normalize_records(rows)}


def create_record_answer(question, record):
    q = question.lower()
    service = record['service_type_description']
    disclaimer = (' Synthetic historical record only; this is not current eligibility or a payment guarantee. '
                  'Amounts apply only to the recorded service; a zero does not establish free coverage.')
    prefix = (f"{service} ({record['coverage_type']}), transaction {record['transaction_id']} "
              f"dated {record['transaction_datetime']}: recorded status {record['coverage_status']}; "
              f"response {record['response_code']}. ")
    unsupported = 'This record does not establish the requested benefit. Select the matching service record or inspect its fields.'
    scopes = {'dental': ('dental',), 'vision': ('vision',), 'pharmacy': ('pharmacy', 'prescription'),
              'medical': ('medical',)}
    for scope, terms in scopes.items():
        if any(term in q for term in terms) and scope != record['coverage_type']:
            return prefix + unsupported + disclaimer
    if any(term in q for term in ('implant', 'surgery', 'emergency', 'hospital', 'therapy', 'family',
                                  'out-of-pocket', 'claim', 'primary care')) or (
            'specialist' in q and 'specialist' not in service.lower()):
        return prefix + unsupported + disclaimer
    answers = []
    money = lambda field: f"${Decimal(record[field]):,.2f}"
    if 'deductible' in q:
        answers.append(f"Recorded deductible total: {money('deductible_total_amount')}; met: {money('deductible_met_amount')}.")
        if 'remaining' in q:
            balance = Decimal(record['deductible_total_amount']) - Decimal(record['deductible_met_amount'])
            answers.append(f"Calculated difference (total minus met): ${balance:,.2f}; this is not a live balance.")
    if 'copay' in q or 'co-pay' in q:
        answers.append(f"Recorded service copay: {money('copay_amount')}.")
    if 'coinsurance' in q:
        answers.append(f"Recorded coinsurance: {record['coinsurance_percentage']}%.")
    if 'authoriz' in q:
        answers.append('Prior authorization recorded as ' + ('required.' if record['prior_authorization_required'] == 'true' else 'not required.'))
    if any(term in q for term in ('status', 'active', 'eligib', 'coverage', 'benefit', 'insurance', 'plan', 'effective', 'end date')):
        answers.append(f"Coverage effective date: {record['coverage_effective_date']}; end date: {record['coverage_end_date'] or 'not supplied'}.")
        answers.append('Plan name is not supplied. No insurer was contacted.')
    if 'limit' in q:
        answers.append(f"Recorded benefit limit: {record['benefit_limit_value']} (type: {record['benefit_limit_type']}); no additional units inferred.")
    if record['coverage_status'] != 'active' or record['response_code'] != 'approved':
        answers.append('The record is not an approved active coverage confirmation; amounts are not a coverage promise.')
    return prefix + (' '.join(answers) if answers else unsupported) + disclaimer
