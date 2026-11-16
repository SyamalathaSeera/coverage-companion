"""Explicit, optional paid OpenAI smoke check using synthetic excerpts only."""
import os
from backend.main import app  # Loads .env, just like the server.
from backend.workflow import run_workflow

if not os.getenv('OPENAI_API_KEY'):
    raise SystemExit('No OPENAI_API_KEY configured. No live request was made.')
result = run_workflow({'mode': 'document', 'question': 'What is the deductible?', 'document': {
    'filename': 'synthetic.pdf', 'pages': [{'page_number': 1, 'text': 'The annual deductible is $1,500.'}]
}})
print({'answer_mode': result['answer_mode'], 'found': result['found']})
if result['answer_mode'] != 'llm_evidence' or not result['found']:
    raise SystemExit('Live smoke check did not produce verified LLM evidence.')
