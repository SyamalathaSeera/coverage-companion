const $ = (selector) => document.querySelector(selector);
const messages = $('#chat-messages');
let busy = false;
let documentInfo = null;
let memberRecords = new Map();
let worklist = [];

function renderWorklist() {
  const filter = $('#review-filter').value;
  const shown = worklist.filter((record) => filter === 'all' ||
    (filter === 'review' ? record.checks.length > 0 : record.checks.some((check) => check.code === 'authorization')));
  $('#worklist-rows').replaceChildren();
  shown.forEach((record) => {
    const row = document.createElement('tr');
    const patient = document.createElement('td');
    const id = document.createElement('strong');
    id.textContent = record.patient_id;
    const service = document.createElement('span');
    service.className = 'cell-note';
    service.textContent = `${record.service} · ${record.transaction_id}`;
    patient.append(id, service);
    const result = document.createElement('td');
    const badge = document.createElement('span');
    badge.className = `review-badge ${record.review_group}`;
    badge.textContent = record.review_label;
    const evidence = document.createElement('span');
    evidence.className = 'cell-note';
    evidence.textContent = `${record.recorded_status} / ${record.response_code} · ${record.recorded_at.slice(0, 10)}`;
    result.append(badge, evidence);
    const action = document.createElement('td');
    action.textContent = record.next_step;
    const open = document.createElement('td');
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Review';
    button.setAttribute('aria-label', `Review ${record.patient_id}, ${record.service}`);
    button.addEventListener('click', () => {
      if (busy) return;
      $('#mode-select').value = 'member';
      $('#member-select').value = record.member_id;
      resetChat();
      $('#record-details').open = true;
      $('#member-panel').scrollIntoView({block: 'start'});
      $('#member-select').focus({preventScroll: true});
    });
    open.append(button);
    row.append(patient, result, action, open);
    $('#worklist-rows').append(row);
  });
  $('#operations-status').textContent = `${shown.length} of ${worklist.length} historical transactions shown. Counts describe this sample only.`;
}

async function loadOperations() {
  try {
    const result = await api('/operations');
    worklist = result.records;
    $('#operations-metrics').replaceChildren();
    const metrics = [['transactions', 'Service records'], ['patients', 'Synthetic patients'],
      ['recorded_exceptions', 'Recorded exceptions'], ['authorization_flags', 'Authorization flags']];
    metrics.forEach(([key, label]) => {
      const card = document.createElement('div');
      card.className = 'metric';
      const number = document.createElement('strong');
      number.textContent = result.summary[key];
      const text = document.createElement('span');
      text.textContent = label;
      card.append(number, text);
      $('#operations-metrics').append(card);
    });
    renderWorklist();
  } catch (error) { $('#operations-status').textContent = `Worklist unavailable: ${error.message}`; }
}

function showSelectedRecord() {
  const member = memberRecords.get($('#member-select').value);
  $('#record-fields').replaceChildren();
  if (!member) return;
  $('#record-source').textContent = member.source || 'Built-in fictional demo record';
  const fields = member.plan.eligibility_record || member.plan;
  Object.entries(fields).forEach(([key, value]) => {
    const term = document.createElement('dt');
    const description = document.createElement('dd');
    term.textContent = key.replaceAll('_', ' ');
    description.textContent = value === '' ? 'Not supplied' : String(value);
    $('#record-fields').append(term, description);
  });
}

async function loadMembers() {
  try {
    const result = await api('/members');
    const selected = $('#member-select').value;
    memberRecords = new Map(result.members.map((member) => [member.member_id, member]));
    const options = result.members.map((member) => {
      const option = document.createElement('option');
      option.value = member.member_id;
      const record = member.plan.eligibility_record;
      option.textContent = record ? `${record.patient_id} · ${record.service_type_description} · ${record.coverage_status} · ${record.transaction_id}` : `${member.member_name} — ${member.member_id}`;
      return option;
    });
    $('#member-select').replaceChildren(...options);
    if (memberRecords.has(selected)) $('#member-select').value = selected;
    const imported = result.members.filter((member) => member.plan.eligibility_record);
    const patients = new Set(imported.map((member) => member.plan.eligibility_record.patient_id)).size;
    $('#member-count').textContent = `${result.members.length - imported.length} demo members + ${imported.length} service transactions for ${patients} synthetic patients.`;
    resetChat();
    await loadOperations();
  } catch (error) {
    $('#member-count').textContent = `Could not load additional records: ${error.message}`;
  }
}

function message(role, text, sources = []) {
  const box = document.createElement('div');
  box.className = `message ${role}`;
  const body = document.createElement('p');
  body.textContent = `${role === 'user' ? 'You' : 'Assistant'}: ${text}`;
  box.append(body);
  sources.forEach((source) => {
    const details = document.createElement('details');
    const summary = document.createElement('summary');
    summary.textContent = `${source.document} · page ${source.page_number}`;
    const quote = document.createElement('blockquote');
    quote.textContent = source.excerpt;
    details.append(summary, quote);
    box.append(details);
  });
  messages.append(box);
  messages.scrollTop = messages.scrollHeight;
}

function setBusy(value, status = '') {
  busy = value;
  document.querySelectorAll('button, input, select').forEach((element) => { element.disabled = value; });
  $('#remove-document').disabled = value || !documentInfo;
  $('#request-status').textContent = status;
}

async function api(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 35000);
  try {
    const response = await fetch(path, { ...options, signal: controller.signal });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(typeof data.detail === 'string' ? data.detail : 'Check your input and try again.');
    }
    return data;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The request timed out. Please try again.');
    if (error instanceof TypeError) throw new Error('Cannot reach the server. Check your connection and try again.');
    throw error;
  } finally { clearTimeout(timer); }
}

function updateDocument(info) {
  documentInfo = info;
  $('#document-status').textContent = info ? `${info.filename} · ${info.page_count} pages · temporary document ready` : 'No document uploaded. Upload one to ask document questions.';
  $('#remove-document').disabled = busy || !info;
}

function resetChat() {
  showSelectedRecord();
  messages.replaceChildren();
  $('#question-input').value = '';
  const isDocument = $('#mode-select').value === 'document';
  $('#member-panel').hidden = isDocument;
  $('#document-panel').hidden = !isDocument;
  const questions = isDocument ? [
    ['Deductible', 'What is the deductible?'], ['Primary care', 'What is the primary care copay?'], ['Prescriptions', 'What are the prescription benefits?']
  ] : memberRecords.get($('#member-select').value)?.plan.eligibility_record ? [
    ['Recorded status', 'What is the recorded coverage status?'], ['Deductible', 'What is the deductible?'],
    ['Service copay', 'What is the copay?'], ['Authorization', 'Is prior authorization required?']
  ] : [['My plan', 'What is my insurance plan?'], ['Deductible', 'What is my deductible?'], ['Copay', 'What is my copay?'], ['Mock status', 'Is my insurance active?']];
  $('#suggestions').replaceChildren();
  questions.forEach(([label, question]) => {
    const button = document.createElement('button');
    button.type = 'button'; button.textContent = label;
    button.addEventListener('click', () => ask(question));
    $('#suggestions').append(button);
  });
  message('assistant', isDocument ? 'Document mode. Upload a synthetic PDF, then ask a specific benefit question. Answers include exact excerpts and page references.' : `Member mode: ${$('#member-select').selectedOptions[0].textContent}. Ask about this fictional record.`);
}

async function ask(question) {
  if (busy || !question.trim()) return;
  const mode = $('#mode-select').value;
  if (mode === 'document' && !documentInfo) { message('assistant', 'Upload a PDF before asking a document question.'); return; }
  message('user', question.trim());
  $('#question-input').value = '';
  setBusy(true, 'Finding an answer…');
  try {
    const result = await api('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mode, member_id: $('#member-select').value, question: question.trim() }) });
    const label = mode === 'member' ? `${result.member_name} · deterministic fictional record` : result.notice;
    message('assistant', `${label}\n\n${result.answer}\n\nSource: ${result.source}`, result.sources);
  } catch (error) { message('assistant', error.message); }
  finally { setBusy(false); $('#question-input').focus(); }
}

$('#chat-form').addEventListener('submit', (event) => { event.preventDefault(); ask($('#question-input').value); });
$('#mode-select').addEventListener('change', resetChat);
$('#member-select').addEventListener('change', resetChat);
$('#review-filter').addEventListener('change', renderWorklist);
$('#upload-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy) return;
  const file = $('#pdf-file').files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.pdf') || file.size > 5 * 1024 * 1024) { $('#document-status').textContent = 'Choose a PDF no larger than 5 MB.'; return; }
  const body = new FormData(); body.append('file', file);
  setBusy(true, 'Uploading and extracting PDF text…');
  try { updateDocument(await api('/documents/upload', { method: 'POST', body })); resetChat(); }
  catch (error) { $('#document-status').textContent = `${error.message} ${documentInfo ? 'Your previous document is still selected.' : ''}`; }
  finally { setBusy(false); $('#pdf-file').value = ''; }
});
$('#remove-document').addEventListener('click', async () => {
  if (busy) return;
  setBusy(true, 'Removing document…');
  try { await api('/documents', { method: 'DELETE' }); updateDocument(null); resetChat(); }
  catch (error) { $('#document-status').textContent = error.message; }
  finally { setBusy(false); }
});
async function refreshDocument() {
  if (busy) return;
  try { updateDocument((await api('/documents')).document); }
  catch (error) { $('#document-status').textContent = error.message; }
}
resetChat();
loadMembers();
refreshDocument();
setInterval(refreshDocument, 60000);
window.addEventListener('focus', refreshDocument);
api('/config').then((config) => { $('#provider-status').textContent = config.llm_configured ? 'OpenAI configured · verified quote selection; extractive fallback on provider errors.' : 'Extractive fallback · no LLM configured or used.'; }).catch(() => { $('#provider-status').textContent = 'Answer mode unavailable until the server reconnects.'; });
