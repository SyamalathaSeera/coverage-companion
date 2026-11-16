"""Only a sanitized summary is traced. Graph and LLM tracing are always disabled."""
import os
from langsmith import traceable, tracing_context


@traceable(name='coverage_request_summary', run_type='chain')
def record_summary(summary):
    return summary


def observe(result):
    if os.getenv('LANGSMITH_TRACING', '').lower() != 'true' or not os.getenv('LANGSMITH_API_KEY'):
        return
    summary = {key: result[key] for key in ('mode', 'answer_mode', 'found', 'route')}
    try:
        with tracing_context(enabled=True, parent=False):
            record_summary(summary)
    except Exception:
        pass  # Optional telemetry must never make a request fail.
