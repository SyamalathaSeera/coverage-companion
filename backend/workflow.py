"""Explicit member/document routing with independent factual data sources."""
import os
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context
from fastapi import HTTPException
from backend.members import find_member, create_answer
from backend.retrieval import retrieve
from backend.llm import select_evidence
from backend.observability import observe
from backend.limits import ProviderAllowanceExceeded

NOT_FOUND = 'The document does not contain a supported answer to this question. Try a specific benefit term. Policy text cannot establish current eligibility or guarantee payment.'


class State(TypedDict, total=False):
    mode: str
    member_id: str
    question: str
    document: dict
    passages: list
    result: dict


def member_lookup(state):
    member_id, member = find_member(state['member_id'])
    return {'result': dict(mode='member', member_id=member_id, member_name=member['member_name'],
        answer=create_answer(state['question'], member['plan']), sources=[],
        source=member.get('source', 'Fictional member records in members.json'), is_demo=True,
        answer_mode='deterministic', found=True, route=['member_lookup'])}


def document_retrieval(state):
    if not state.get('document'):
        raise HTTPException(409, 'Upload a PDF first. Your previous document may have expired.')
    # A policy is not evidence of a live member event.
    q = state['question'].lower()
    live = any(term in q for term in ('claim status', 'my claim', 'currently active', 'am i eligible', 'current eligibility', 'guarantee payment', 'insurance active'))
    return {'passages': [] if live else retrieve(state['question'], state['document'])}


def document_answer(state):
    passages = state['passages']
    answer_mode = 'extractive_fallback'
    notice = 'Extractive fallback: no LLM used. These are matching passages; read the terms and exclusions.'
    if not passages:
        notice = 'Extractive fallback: no LLM used. No supporting passage found.'
    if passages and os.getenv('OPENAI_API_KEY'):
        try:
            passages = select_evidence(state['question'], passages)
            answer_mode = 'llm_evidence'
            notice = 'OpenAI selected supporting quotes; the backend verified each quote against the document.'
        except ProviderAllowanceExceeded:
            notice = 'The daily AI request allowance has been reached. Extractive fallback: matching passages are shown.'
        except Exception:
            notice = 'OpenAI was unavailable or returned unsupported evidence. Extractive fallback: no LLM answer is shown.'
    answer = '\n\n'.join(p['excerpt'] for p in passages) if passages else NOT_FOUND
    return {'result': dict(mode='document', answer=answer, sources=passages,
        source=state['document']['filename'], answer_mode=answer_mode, notice=notice,
        found=bool(passages), is_demo=True, route=['document_retrieval', 'document_answer'])}


builder = StateGraph(State)
builder.add_node('member_lookup', member_lookup)
builder.add_node('document_retrieval', document_retrieval)
builder.add_node('document_answer', document_answer)
builder.add_conditional_edges(START, lambda state: state['mode'], {'member': 'member_lookup', 'document': 'document_retrieval'})
builder.add_edge('member_lookup', END)
builder.add_edge('document_retrieval', 'document_answer')
builder.add_edge('document_answer', END)
workflow = builder.compile()


def run_workflow(state):
    with tracing_context(enabled=False):
        result = workflow.invoke(state)['result']
    observe(result)
    return result
