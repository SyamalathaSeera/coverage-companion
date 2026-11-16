"""Project-owned fictional service records for fresh installations."""
from backend.gomask import as_members


def sample_members():
    scenarios = [
        ('medical', 'Office visit', 'active', 'approved', False, '900', '125', '30', '20'),
        ('dental', 'Routine dental exam', 'active', 'approved', False, '180', '40', '35', '10'),
        ('pharmacy', 'Retail prescriptions', 'terminated', 'denied', False, '60', '60', '12', '0'),
        ('medical', 'Specialist consultation', 'pending', 'pending', True, '1700', '0', '55', '15'),
        ('vision', 'Routine vision exam', 'active', 'approved', False, '90', '20', '18', '0'),
        ('medical', 'Outpatient consultation', 'inactive', 'error', True, '2200', '0', '65', '25'),
        ('dental', 'Preventive dental visit', 'active', 'approved', False, '280', '100', '40', '15'),
        ('pharmacy', 'Generic prescriptions', 'active', 'approved', False, '80', '15', '8', '5'),
        ('medical', 'Urgent care visit', 'active', 'approved', False, '1200', '450', '60', '20'),
        ('medical', 'Outpatient imaging', 'active', 'approved', True, '2000', '800', '90', '25'),
        ('medical', 'Physical therapy', 'pending', 'pending', True, '1500', '300', '45', '15'),
        ('medical', 'Laboratory testing', 'active', 'approved', False, '1000', '1000', '0', '10'),
    ]
    rows = []
    for index, (kind, service, status, response, auth, total, met, copay, coinsurance) in enumerate(scenarios, 1):
        rows.append(dict(transaction_id=f'SAMPLE{index:03}', patient_id=f'SYN{index:03}',
            payer_id='SAMPLE-PAYER', provider_id='SAMPLE-PROVIDER', coverage_type=kind,
            service_type_description=service, coverage_status=status, response_code=response,
            prior_authorization_required=str(auth).lower(), deductible_total_amount=total,
            deductible_met_amount=met, copay_amount=copay, coinsurance_percentage=coinsurance,
            coverage_effective_date='2024-01-01', coverage_end_date='2024-06-30' if status == 'terminated' else '',
            transaction_datetime='2025-01-15T12:00:00', benefit_limit_type='not specified',
            benefit_limit_value='0', service_type_code='sample',
            response_message='Project-generated fictional scenario for software testing.'))
    for row in rows[8:]:
        row['provider_id'] = 'SAMPLE-PROVIDER-' + row['transaction_id'][-3:]
        row['payer_id'] = 'SAMPLE-PAYER-MEDICAL'
    rows[10].update(benefit_limit_type='visits', benefit_limit_value='12')
    imported = as_members(rows)
    return {key.replace('GM-', 'SYN-', 1): {**member, 'source': 'Coverage Companion fictional service records',
            'source_url': ''} for key, member in imported.items()}
