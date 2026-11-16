"""Offline evaluation by default. --langsmith uploads synthetic data only."""
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from backend.documents import extract_pdf_text
from backend.workflow import run_workflow
from scripts.make_sample_pdf import make_pdf

DATASET = json.loads((Path(__file__).parent / 'dataset.json').read_text())
DOCUMENT = {'filename': 'synthetic-benefits.pdf', 'pages': extract_pdf_text(make_pdf())}


def target(inputs):
    # Deterministic evaluation never calls OpenAI, even when a key exists.
    from unittest.mock import patch
    with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'LANGSMITH_TRACING': 'false'}):
        return run_workflow({**inputs, 'document': DOCUMENT})


def scores(inputs, outputs, reference_outputs):
    sources = outputs['sources']
    supported = all(any(source['excerpt'] in page['text'] and source['page_number'] == page['page_number'] for page in DOCUMENT['pages']) for source in sources)
    if inputs['mode'] == 'document' and outputs['found']:
        supported = supported and outputs['answer'] == '\n\n'.join(source['excerpt'] for source in sources)
    return [
        {'key': 'expected_answer', 'score': reference_outputs['contains'] in outputs['answer']},
        {'key': 'source_pages', 'score': sorted(set(s['page_number'] for s in sources)) == reference_outputs['pages']},
        {'key': 'document_support', 'score': supported and (bool(sources) if inputs['mode'] == 'document' and outputs['found'] else True)},
        {'key': 'found_or_abstain', 'score': outputs['found'] == reference_outputs['found']},
    ]


def main():
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
    parser = argparse.ArgumentParser()
    parser.add_argument('--langsmith', action='store_true', help='Upload this synthetic dataset and evaluate in LangSmith (network required).')
    args = parser.parse_args()
    if args.langsmith:
        if not os.getenv('LANGSMITH_API_KEY'):
            raise SystemExit('Set LANGSMITH_API_KEY before running --langsmith.')
        from datetime import datetime, timezone
        from langsmith import Client
        client = Client()
        dataset = client.create_dataset(dataset_name='coverage-synthetic-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
        client.create_examples(dataset_id=dataset.id, examples=DATASET)
        client.evaluate(target, data=dataset.id, evaluators=[scores], experiment_prefix='coverage-offline', max_concurrency=1)
    else:
        passed = 0
        for example in DATASET:
            results = scores(example['inputs'], target(example['inputs']), example['outputs'])
            passed += all(result['score'] for result in results)
            print(example['inputs']['question'], results)
        print(f'{passed}/{len(DATASET)} examples passed all four checks.')
        raise SystemExit(0 if passed == len(DATASET) else 1)


if __name__ == '__main__':
    main()
