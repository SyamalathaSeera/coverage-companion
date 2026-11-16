"""FastAPI entry point. Run one worker because document sessions live in memory."""
import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.documents import MAX_FILE_BYTES, extract_pdf_text
from backend.members import find_member, MEMBERS
from backend.operations import build_worklist
from backend.limits import WindowLimiter, configured_limit
from backend.storage import DocumentStore, SESSION_SECONDS

load_dotenv(Path(__file__).resolve().parent.parent / '.env')
from backend.workflow import run_workflow

COOKIE = 'coverage_session'


@asynccontextmanager
async def lifespan(app):
    app.state.request_limiter = WindowLimiter()
    async def sweep():
        while True:
            await asyncio.sleep(60)
            app.state.documents.cleanup()
    task = asyncio.create_task(sweep())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    app.state.documents.records.clear()


app = FastAPI(title='Coverage Companion', lifespan=lifespan)
app.state.documents = DocumentStore()
app.state.request_limiter = WindowLimiter()


class BodyLimit:
    """Cap actual streamed bytes before Starlette parses multipart or JSON."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in ('POST', 'PUT', 'PATCH'):
            return await self.app(scope, receive, send)
        limit = MAX_FILE_BYTES + 65536 if scope['path'] == '/documents/upload' else 8192
        chunks, size = [], 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            size += len(message.get('body', b''))
            if size > limit:
                return await JSONResponse({'detail': 'Request is too large. PDFs must be at most 5 MB.'}, 413)(scope, receive, send)
            chunks.append(message)
            if not message.get('more_body', False):
                break
        async def replay():
            return chunks.pop(0) if chunks else await receive()
        await self.app(scope, replay, send)


app.add_middleware(BodyLimit)


@app.middleware('http')
async def browser_security(request, call_next):
    if request.method in ('POST', 'DELETE'):
        origin = request.headers.get('origin')
        expected = os.getenv('APP_ORIGIN') or str(request.base_url).rstrip('/')
        if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin != expected):
            return JSONResponse({'detail': 'Use this application from its own website.'}, 403)
    if request.method == 'POST' and request.url.path in ('/chat', '/documents/upload'):
        upload = request.url.path == '/documents/upload'
        limit = configured_limit('UPLOADS_PER_MINUTE' if upload else 'CHAT_REQUESTS_PER_MINUTE', 10 if upload else 60)
        allowed, retry_after = app.state.request_limiter.allow('uploads' if upload else 'chat', limit, 60)
        if not allowed:
            return JSONResponse({'detail': 'The workspace request allowance has been reached. Please try again shortly.'},
                                429, headers={'Retry-After': str(retry_after), 'Cache-Control': 'no-store'})
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if request.url.path.startswith(('/chat', '/plan', '/documents', '/members', '/operations')):
        response.headers['Cache-Control'] = 'no-store'
    else:
        response.headers['Cache-Control'] = 'no-cache'
    return response


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    return JSONResponse({'detail': 'The request could not be completed. Please try again.'}, 500)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['member', 'document'] = 'member'
    member_id: str = Field(default='DEMO001', min_length=1, max_length=30)
    question: str = Field(min_length=1, max_length=500)
    previous_question: str = Field(default='', max_length=500)

    @field_validator('question', 'member_id')
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError('Please enter a nonblank value.')
        return value.strip()


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/config')
def config():
    return {'llm_configured': bool(os.getenv('OPENAI_API_KEY')), 'session_minutes': SESSION_SECONDS // 60}


@app.get('/plan')
def plan(member_id: str = 'DEMO001'):
    normalized, member = find_member(member_id)
    return dict(member_id=normalized, **member, is_demo=True,
                **({} if 'source' in member else {'source': 'Fictional member records in members.json'}))


@app.get('/members')
def members():
    return {'members': [dict(member_id=key, **member) for key, member in MEMBERS.items()], 'is_demo': True}


@app.get('/operations')
def operations():
    return build_worklist(MEMBERS)


@app.post('/chat')
def chat(body: ChatRequest, request: Request):
    document = app.state.documents.get(request.cookies.get(COOKIE)) if body.mode == 'document' else None
    return run_workflow(dict(mode=body.mode, member_id=body.member_id, question=body.question,
                             previous_question=body.previous_question, document=document))


def metadata(document):
    remaining = max(0, int(document['deadline'] - app.state.documents.clock()))
    return dict(filename=document['filename'], page_count=len(document['pages']), expires_in_seconds=remaining)


@app.post('/documents/upload')
def upload_document(request: Request, response: Response, file: UploadFile = File(...)):
    try:
        if not (file.filename or '').lower().endswith('.pdf'):
            raise HTTPException(400, 'Please upload a PDF file.')
        contents = file.file.read(MAX_FILE_BYTES + 1)
        pages = extract_pdf_text(contents)
        # A basename is display-only and never used as a filesystem path.
        name = (file.filename or 'benefits.pdf').replace('\\', '/').split('/')[-1][:150]
        key, document = app.state.documents.put(request.cookies.get(COOKIE), name, pages)
        response.set_cookie(COOKIE, key, max_age=SESSION_SECONDS, httponly=True,
                          secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true', samesite='strict')
        return {**metadata(document), 'message': 'PDF ready. Any previous document in this browser was replaced.'}
    finally:
        file.file.close()


@app.get('/documents')
def document_status(request: Request):
    document = app.state.documents.get(request.cookies.get(COOKIE))
    return {'document': metadata(document) if document else None}


@app.delete('/documents')
def delete_document(request: Request, response: Response):
    app.state.documents.remove(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE)
    return {'message': 'Document removed.'}


app.mount('/', StaticFiles(directory=str(Path(__file__).resolve().parent.parent / 'frontend'), html=True), name='frontend')
