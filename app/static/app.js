'use strict';

const $ = id => document.getElementById(id);
const messages   = $('messages');
const userInput  = $('user-input');
const sendBtn    = $('send-btn');
const loading    = $('loading');
const incidentList = $('incident-list');
const apiDot     = $('api-dot');
const statusText = $('status-text');

// ─── Health check ────────────────────────────────────────────────
async function checkHealth() {
  try {
    const r = await fetch('/api/health');
    if (r.ok) {
      apiDot.classList.remove('offline');
      statusText.textContent = 'API Vigie connectée';
    } else throw new Error();
  } catch {
    apiDot.classList.add('offline');
    statusText.textContent = 'API hors ligne';
  }
}

// ─── Render helpers ──────────────────────────────────────────────
function sep() {
  const d = document.createElement('div');
  d.className = 'sep';
  d.textContent = '─'.repeat(60);
  return d;
}

function appendUserMsg(text) {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-user';
  wrap.innerHTML = `
    <div class="msg-prompt">[ANALYSTE] &gt;</div>
    <div class="msg-body">${escHtml(text)}</div>`;
  messages.appendChild(sep());
  messages.appendChild(wrap);
  scrollBottom();
}

function appendAgentMsg(data) {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-agent';

  const techHtml = data.techniques.map(t => {
    const cls = `tech-badge sev-${t.severity}`;
    return `<span class="${cls}" title="${escHtml(t.tactic)}">${escHtml(t.id)} ${escHtml(t.name)}</span>`;
  }).join('');

  const guardrailHtml = data.requires_review ? renderGuardrail(data.incident_id) : '';

  wrap.innerHTML = `
    <div class="msg-prompt">[VIGIE] &gt;</div>
    <div class="msg-body">${escHtml(data.analysis)}</div>
    ${techHtml ? `<div class="techniques">${techHtml}</div>` : ''}
    ${guardrailHtml}`;

  messages.appendChild(wrap);
  scrollBottom();

  if (data.requires_review) wireGuardrailBtns(wrap, data.incident_id);
}

function renderGuardrail(incidentId) {
  return `
    <div class="guardrail-block" data-incident="${incidentId}">
      <div class="guardrail-label">&#9658; GUARDRAIL AI Act art.14 — Validation humaine requise</div>
      <div style="color:var(--crt-text);font-size:11px;">Cette recommandation implique une technique haute-sévérité. Une validation humaine est obligatoire avant toute action.</div>
      <div class="guardrail-btns">
        <button class="g-btn g-btn-approve" data-action="approved">[A]pprouver</button>
        <button class="g-btn g-btn-reject"  data-action="rejected">[R]ejeter</button>
        <button class="g-btn g-btn-detail"  data-action="detail">[D]étails</button>
      </div>
    </div>`;
}

function wireGuardrailBtns(wrap, incidentId) {
  const block = wrap.querySelector('.guardrail-block');
  if (!block) return;
  block.querySelectorAll('.g-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const action = btn.dataset.action;
      if (action === 'detail') {
        appendDetailMsg(incidentId);
        return;
      }
      await submitReview(incidentId, action, block);
    });
  });
}

async function submitReview(incidentId, action, block) {
  const btns = block.querySelectorAll('.g-btn');
  btns.forEach(b => b.disabled = true);
  try {
    const r = await fetch(`/api/incidents/${incidentId}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    const label = action === 'approved' ? '▸ Approuvée — audit enregistré' : '▸ Rejetée — audit enregistré';
    const done = document.createElement('div');
    done.className = 'guardrail-done';
    done.textContent = label;
    block.appendChild(done);
    btns.forEach(b => b.style.display = 'none');
    await loadIncidents();
  } catch (e) {
    appendErrorMsg(`Erreur guardrail : ${e.message}`);
    btns.forEach(b => b.disabled = false);
  }
}

function appendDetailMsg(incidentId) {
  const d = document.createElement('div');
  d.className = 'msg';
  d.innerHTML = `<div class="msg-prompt">[VIGIE] &gt;</div>
    <div class="msg-body" style="color:var(--crt-text)">
─── DÉTAILS INCIDENT #${incidentId} ───────────────────────────<br>
Consultez le panel "Incidents" pour l'historique complet.<br>
Audit log : toute action de review est enregistrée en base sqlite de façon atomique.</div>`;
  messages.appendChild(d);
  scrollBottom();
}

function appendErrorMsg(text) {
  const d = document.createElement('div');
  d.className = 'msg msg-error';
  d.innerHTML = `<div class="msg-prompt">[ERREUR] &gt;</div><div class="msg-body">${escHtml(text)}</div>`;
  messages.appendChild(d);
  scrollBottom();
}

function appendWelcome() {
  const d = document.createElement('div');
  d.className = 'msg msg-agent';
  d.innerHTML = `
    <div class="msg-prompt">[VIGIE] &gt;</div>
    <div class="msg-body">
Vigie SOC v2.0 — Système de réponse aux incidents MITRE ATT&CK<br>
──────────────────────────────────────────────────────<br>
Base de connaissances : 10 techniques ATT&CK chargées<br>
Guardrail AI Act art.14 : actif<br>
Audit log : sqlite transactionnel<br>
──────────────────────────────────────────────────────<br>
Décrivez un incident de sécurité pour commencer l'analyse.</div>`;
  messages.appendChild(d);
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function scrollBottom() {
  messages.scrollTop = messages.scrollHeight;
}

// ─── Send message ────────────────────────────────────────────────
async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = '';
  sendBtn.disabled = true;
  userInput.disabled = true;
  loading.classList.add('active');

  appendUserMsg(text);

  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    const data = await r.json();
    appendAgentMsg(data);
    await loadIncidents();
  } catch (e) {
    appendErrorMsg(`Analyse échouée : ${e.message}`);
  } finally {
    loading.classList.remove('active');
    sendBtn.disabled = false;
    userInput.disabled = false;
    userInput.focus();
  }
}

// ─── Incidents sidebar ───────────────────────────────────────────
async function loadIncidents() {
  try {
    const r = await fetch('/api/incidents');
    const items = await r.json();
    incidentList.innerHTML = '';
    if (!items.length) {
      incidentList.innerHTML = '<div style="padding:6px;color:#666;font-size:11px;">Aucun incident</div>';
      return;
    }
    items.forEach(inc => {
      const d = document.createElement('div');
      d.className = 'incident-item';
      const statusClass = `i-${inc.status}`;
      const label = inc.status === 'pending' ? 'en attente' : inc.status === 'approved' ? 'approuvé' : 'rejeté';
      d.innerHTML = `
        <div>#${inc.id} — ${escHtml(inc.description.substring(0, 40))}${inc.description.length > 40 ? '…' : ''}</div>
        <div class="incident-status ${statusClass}">${label} | ${inc.created_at.substring(0, 16)}</div>`;
      incidentList.appendChild(d);
    });
  } catch { /* sidebar non critique */ }
}

// ─── Keyboard shortcuts ──────────────────────────────────────────
userInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
sendBtn.addEventListener('click', sendMessage);
$('btn-new').addEventListener('click', () => { userInput.focus(); });
$('btn-incidents').addEventListener('click', loadIncidents);

// ─── Init ────────────────────────────────────────────────────────
checkHealth();
loadIncidents();
appendWelcome();
