FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY backend ./backend
COPY frontend ./frontend
RUN useradd --create-home demo
USER demo
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/health', timeout=2)"
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --no-access-log"]
