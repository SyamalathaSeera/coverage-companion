"""Generate a reproducible synthetic PDF for the demo and tests."""
from io import BytesIO
from reportlab.pdfgen import canvas

PAGES = [
    'SYNTHETIC BENEFITS SUMMARY - NOT REAL INSURANCE\nAnnual deductible: $1,500 for an individual.\nThe primary care copay is $25 per visit.\nSpecialist visits have a $50 copay.\nAll amounts are fictional plan terms, not current eligibility.',
    'SYNTHETIC PRESCRIPTION BENEFITS\nGeneric prescription drugs have a $10 copay for a 30-day supply.\nBrand prescription drugs have a $35 copay for a 30-day supply.\nOut-of-network benefits are not included in this sample.\nPolicy terms do not guarantee payment.',
]


def make_pdf(pages=PAGES):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    for page in pages:
        text = pdf.beginText(50, 790)
        for line in page.splitlines():
            text.textLine(line)
        pdf.drawText(text)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


if __name__ == '__main__':
    from pathlib import Path
    target = Path(__file__).resolve().parent.parent / 'docs' / 'synthetic-benefits.pdf'
    target.write_bytes(make_pdf())
    print(f'Created {target}')
