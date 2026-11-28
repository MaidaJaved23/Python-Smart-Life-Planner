/* Smart Life Planner frontend (plain JavaScript, no build step).
   Talks to server.py through /api/*. Every record comes from your JSON files:
   data/destinations.json, data/trips.json, data/budgets.json, config/developer.json and reports/*.pdf. */
(function () {
'use strict';

/* ------------------------------------------------------------------ helpers */
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const root = $('#root');
const state = { user: null, ready: false, destinations: null, next: null };
let renderToken = 0;

const money = n => {
  n = Number(n);
  if (!isFinite(n)) return 'n/a';
  const a = Math.abs(n);
  const s = a.toLocaleString('en-US', { minimumFractionDigits: Number.isInteger(a) ? 0 : 2, maximumFractionDigits: 2 });
  return (n < 0 ? '-' : '') + 'PKR ' + s;
};
const pad = n => String(n).padStart(2, '0');
const isoLocal = d => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
const todayISO = () => isoLocal(new Date());
const parseISO = s => {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s || '');
  if (!m) return null;
  const d = new Date(+m[1], +m[2] - 1, +m[3]);
  return d.getMonth() === +m[2] - 1 ? d : null;
};
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const fmtDate = d => d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
const fmtISO = s => { const d = parseISO(s); return d ? fmtDate(d) : 'Not set'; };
const num = v => { if (v === '' || v == null) return NaN; return Number(String(v).replace(/,/g, '').trim()); };
const firstName = n => String(n || '').trim().split(/\s+/)[0] || 'there';
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/* backend objects are serialised by server.plain(); look fields up by name pattern so small naming differences do not break the page */
const pick = (o, re, type) => {
  if (!o || typeof o !== 'object') return undefined;
  for (const k of Object.keys(o)) if (re.test(k) && (!type || typeof o[k] === type)) return o[k];
  return undefined;
};
const numOf = (o, re) => {
  const v = pick(o, re);
  if (v === undefined || v === null || v === '') return null;
  const n = Number(v);
  return isFinite(n) ? n : null;
};

const ICONS = {
  home: '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  route: '<circle cx="6" cy="19" r="2.5"/><circle cx="18" cy="5" r="2.5"/><path d="M8.5 19H15a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h6.5"/>',
  bag: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M3 13h18"/>',
  pin: '<path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
  wallet: '<path d="M3 7a2 2 0 0 1 2-2h13v4"/><path d="M3 7v11a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2z"/><circle cx="16.5" cy="14.5" r="1.2"/>',
  file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.5"/>',
  alert: '<path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18v.5"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  out: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
  down: '<path d="M12 4v12M7 11l5 5 5-5M5 20h14"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2.2 2.2L15.5 10"/>',
  spark: '<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/>',
  scale: '<path d="M12 4v16M6 20h12M5 7h14M5 7l-3 7a3.5 3.5 0 0 0 6 0zM19 7l-3 7a3.5 3.5 0 0 0 6 0z"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/>'
};
const icon = (n, extra) => '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ' + (extra || '') + '>' + (ICONS[n] || '') + '</svg>';
const LOGO = '<svg viewBox="0 0 32 32" aria-hidden="true"><defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#22D3EE"/><stop offset="1" stop-color="#9B7BFF"/></linearGradient></defs><rect width="32" height="32" rx="9" fill="#0C1330" stroke="url(#lg)" stroke-width="1.4"/><path d="M16 5.5a7 7 0 0 0-7 7c0 5 7 12 7 12s7-7 7-12a7 7 0 0 0-7-7z" fill="none" stroke="url(#lg)" stroke-width="2.2"/><circle cx="16" cy="12.5" r="2.6" fill="#FF4D8D"/></svg>';

class ApiError extends Error { constructor(m, status) { super(m); this.status = status; } }

async function api(method, url, body) {
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: 'same-origin'
    });
  } catch (e) {
    throw new ApiError('Cannot reach the server. Make sure python server.py is running, then try again.', 0);
  }
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (e) { /* not JSON */ }
  if (!res.ok) {
    if (res.status === 401 && !/\/(login|signup|me)$/.test(url)) {
      state.user = null;
      toast('Your session ended. Log in again to continue.', 'bad');
      go('#/login');
    }
    throw new ApiError((data && data.error) || 'The request failed (' + res.status + ').', res.status);
  }
  return data;
}

function toast(msg, type) {
  const t = document.createElement('div');
  t.className = 'toast ' + (type || '');
  t.innerHTML = (type === 'bad' ? icon('alert', 'width="20" height="20" style="flex:none;color:var(--pk)"') : type === 'ok' ? icon('check', 'width="20" height="20" style="flex:none;color:var(--gr)"') : '') + '<span>' + esc(msg) + '</span>';
  $('#toasts').appendChild(t);
  setTimeout(() => t.remove(), 5200);
}

function busy(btn, on, label) {
  if (!btn) return;
  if (on) { btn.dataset.l = btn.innerHTML; btn.disabled = true; btn.innerHTML = '<span class="spin"></span> ' + esc(label || 'Working'); }
  else { btn.disabled = false; if (btn.dataset.l) btn.innerHTML = btn.dataset.l; }
}

/* dialog */
const dlg = $('#dlg');
dlg.addEventListener('close', () => { dlg.innerHTML = ''; });   // no stale form fields left in the page
function openDialog(html, opts) {
  opts = opts || {};
  dlg.className = 'dlg' + (opts.wide ? ' wide' : '');
  dlg.innerHTML = '<div class="dbody">' + html + '</div>';
  dlg.onclose = opts.onclose || null;
  if (!dlg.open) dlg.showModal();
  $$('[data-close]', dlg).forEach(b => b.addEventListener('click', () => dlg.close()));
  const first = $('input:not([type=hidden]),select,textarea', dlg);
  if (first && !opts.noFocus) first.focus();
  return dlg;
}
function closeDialog() { if (dlg.open) { dlg.onclose = null; dlg.close(); } }
function confirmDialog(title, msg, label, danger) {
  return new Promise(resolve => {
    let done = false;
    openDialog('<h2>' + esc(title) + '</h2><p class="muted">' + esc(msg) + '</p><div class="dfoot"><button class="btn btn-ghost" data-close type="button">Cancel</button><button class="btn ' + (danger ? 'btn-danger' : 'btn-primary') + '" id="cd-ok" type="button">' + esc(label) + '</button></div>',
      { noFocus: true, onclose: () => { if (!done) resolve(false); } });
    $('#cd-ok', dlg).addEventListener('click', () => { done = true; closeDialog(); resolve(true); });
    $('#cd-ok', dlg).focus();
  });
}

/* forms */
function setErr(input, msg) {
  if (!input) return;
  const box = document.getElementById('e-' + input.id);
  if (msg) { input.setAttribute('aria-invalid', 'true'); if (box) box.textContent = msg; }
  else { input.removeAttribute('aria-invalid'); if (box) box.textContent = ''; }
}
function clearErrs(form) { $$('[aria-invalid]', form).forEach(i => setErr(i, '')); const fe = $('.formerr', form); if (fe) fe.textContent = ''; }
function fieldErrors(form, errs) {
  clearErrs(form);
  let first = null;
  Object.keys(errs).forEach(id => { const el = $('#' + id, form); if (el) { setErr(el, errs[id]); if (!first) first = el; } });
  if (first) first.focus();
  return !first;
}
const fld = (id, label, control, hint) =>
  '<div class="field"><label for="' + id + '">' + label + '</label>' + control + (hint ? '<div class="hint" id="h-' + id + '">' + hint + '</div>' : '') + '<div class="err" id="e-' + id + '" role="alert"></div></div>';

/* downloads: PDFs are written by pdf_generator.py into reports/ and fetched from /api/reports/<name> */
async function download(name) {
  try {
    const res = await fetch('/api/reports/' + encodeURIComponent(name), { credentials: 'same-origin' });
    if (!res.ok) {
      let m = 'Could not download the file.';
      try { m = (await res.json()).error || m; } catch (e) { /* ignore */ }
      throw new Error(m);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    toast('Downloaded ' + name, 'ok');
  } catch (e) { toast(e.message, 'bad'); }
}

/* trip dates are not stored by the backend Trip model, so keep them next to the trip id in this browser */
const DATE_KEY = 'slp.tripDates';
function tripDates() { try { return JSON.parse(localStorage.getItem(DATE_KEY) || '{}') || {}; } catch (e) { return {}; } }
function saveTripDate(id, iso) { if (!id || !iso) return; try { const m = tripDates(); m[id] = iso; localStorage.setItem(DATE_KEY, JSON.stringify(m)); } catch (e) { /* storage blocked */ } }

/* ------------------------------------------------------------------ data normalisers */
async function getDestinations(force) {
  if (state.destinations && !force) return state.destinations;
  const raw = await api('GET', '/api/destinations');
  const list = Array.isArray(raw) ? raw : (raw && (raw.destinations || raw.data)) || [];
  state.destinations = list.map(d => ({
    id: d.id != null ? d.id : (d.destination_id != null ? d.destination_id : d.name),
    name: d.name || String(d.id),
    category: d.category || d.type || 'Other',
    region: d.region || '',
    description: d.description || '',
    capacity: numOf(d, /capacity/i),
    transport: numOf(d, /transport/i),
    hotel: numOf(d, /accom|hotel|room/i),
    food: numOf(d, /food|dining|meal/i),
    activities: numOf(d, /activit/i),
    attractions: Array.isArray(d.attractions) ? d.attractions : []
  }));
  return state.destinations;
}

function breakdown(trip) {
  const b = trip && trip.cost_breakdown;
  if (!b || typeof b !== 'object') return null;
  const parts = [
    { label: 'Transport', v: numOf(b, /transport/i), c: 'var(--cy)' },
    { label: 'Accommodation', v: numOf(b, /accom|hotel|stay/i), c: 'var(--vi)' },
    { label: 'Food and dining', v: numOf(b, /food|dining|meal/i), c: 'var(--gr)' },
    { label: 'Activities', v: numOf(b, /activit/i), c: 'var(--pk)' },
    { label: 'Emergency allowance (5%)', v: numOf(b, /emerg/i), c: 'var(--am)' }
  ].filter(p => p.v !== null);
  const sum = parts.reduce((a, p) => a + p.v, 0);
  let total = numOf(b, /^total/i);
  if (total === null) total = sum;
  let perPerson = numOf(b, /per_?person/i);
  if (perPerson === null && trip.travellers > 0) perPerson = total / trip.travellers;
  return { parts, total, perPerson, rooms: numOf(b, /room/i), subtotal: numOf(b, /subtotal|operational/i) };
}

function verdictOf(trip, status) {
  const s = String(status || trip.status || '').toLowerCase();
  if (s.includes('over')) return 'over';
  if (s.includes('exact')) return 'exact';
  if (s) return 'ok';
  const bd = breakdown(trip);
  if (bd && Number(trip.budget) > 0) {
    const diff = Number(trip.budget) - bd.total;
    return diff < -0.005 ? 'over' : Math.abs(diff) < 0.01 ? 'exact' : 'ok';
  }
  return 'ok';
}
const VERDICT = {
  ok: { badge: 'ok', text: 'Within budget', icon: 'check' },
  exact: { badge: 'exact', text: 'Exactly within budget', icon: 'scale' },
  over: { badge: 'over', text: 'Over budget', icon: 'alert' }
};
const verdictBadge = (trip, status) => { const v = VERDICT[verdictOf(trip, status)]; return '<span class="badge ' + v.badge + '">' + v.text + '</span>'; };

function normBudget(v) {
  const b = (v && v.budget) || v || {};
  let planned = b.planned_categories || b.categories || {};
  if (Array.isArray(planned)) { const m = {}; planned.forEach(p => { m[p.name || p.category] = Number(p.planned || p.planned_amount || 0); }); planned = m; }
  const expenses = (b.expenses || []).map(e => ({
    id: e.expense_id || e.id, date: e.date || '', category: e.category || 'Uncategorised',
    amount: Number(e.amount) || 0, description: e.description || ''
  }));
  const spentBy = {};
  expenses.forEach(e => { spentBy[e.category] = (spentBy[e.category] || 0) + e.amount; });
  const names = Array.from(new Set(Object.keys(planned).concat(Object.keys(spentBy))));
  const rows = names.map(name => ({ name, planned: Number(planned[name]) || 0, spent: spentBy[name] || 0, inPlan: name in planned }));
  const available = Number(b.total_available) || 0;
  const totalPlanned = rows.reduce((a, r) => a + r.planned, 0);
  const totalSpent = rows.reduce((a, r) => a + r.spent, 0);
  const remaining = available - totalSpent;
  return {
    id: b.budget_id || b.id, month: b.month || '', type: b.budget_type || '', available, rows, expenses,
    totalPlanned, totalSpent, remaining, savingsPct: available > 0 ? (remaining / available) * 100 : 0,
    overall: available > 0 ? totalSpent / available : 0
  };
}
const barClass = ratio => ratio > 1 ? 'bad' : ratio > 0.85 ? 'warn' : '';

/* ------------------------------------------------------------------ router */
const PROTECTED = ['dashboard', 'plan', 'trips', 'destinations', 'budgets', 'reports', 'settings'];
function go(hash) { if (location.hash === hash) render(); else location.hash = hash; }
const NAV = [
  ['dashboard', 'Dashboard', 'home'], ['plan', 'Plan a trip', 'route'], ['trips', 'My trips', 'bag'],
  ['destinations', 'Destinations', 'pin'], ['budgets', 'Budgets', 'wallet'], ['reports', 'PDF reports', 'file'], ['settings', 'Settings', 'gear']
];

async function render() {
  const token = ++renderToken;
  closeDialog();
  const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean).map(decodeURIComponent);
  const name = parts[0] || '';
  window.scrollTo(0, 0);
  if (!state.ready) return;
  const authed = !!state.user;
  if (authed && (name === '' || name === 'login' || name === 'signup')) return go('#/dashboard');
  if (!authed && PROTECTED.includes(name)) { state.next = location.hash; return go('#/login'); }
  if (!authed) {
    if (name === 'login') return pageLogin();
    if (name === 'signup') return pageSignup();
    return pageLanding();
  }
  const view = mountShell(PROTECTED.includes(name) ? name : 'dashboard');
  view.onclick = null;
  view.innerHTML = skeleton();
  document.title = (NAV.find(n => n[0] === name) || NAV[0])[1] + ' | Smart Life Planner';
  try {
    const pages = { dashboard: pageDashboard, plan: pagePlan, trips: pageTrips, destinations: pageDestinations, budgets: pageBudgets, reports: pageReports, settings: pageSettings };
    const fn = pages[name] || pageDashboard;
    await fn(view, parts.slice(1), () => token === renderToken);
  } catch (e) {
    if (token !== renderToken) return;
    view.innerHTML = errorBox(e.message);
    const r = $('#retry', view); if (r) r.addEventListener('click', render);
  }
  if (token === renderToken) { view.focus({ preventScroll: true }); }
}
function skeleton() {
  return '<div class="sk" style="height:38px;width:260px;margin-bottom:26px"></div><div class="stats"><div class="sk" style="height:92px"></div><div class="sk" style="height:92px"></div><div class="sk" style="height:92px"></div></div><div class="sk" style="height:240px"></div>';
}
function errorBox(msg) {
  return '<div class="empty tint-pk" role="alert">' + icon('alert') + '<h3>This page did not load</h3><p>' + esc(msg) + '</p><button class="btn btn-primary" id="retry" type="button">Try again</button></div>';
}

function mountShell(active) {
  if (!$('.shell')) {
    const u = state.user;
    root.innerHTML = '<div class="shell"><aside class="side" id="side" aria-label="Main menu"><a class="brand" href="#/dashboard">' + LOGO + 'Smart Life Planner</a><nav>' +
      NAV.map(n => '<a href="#/' + n[0] + '" data-nav="' + n[0] + '">' + icon(n[2]) + n[1] + '</a>').join('') +
      '</nav><div class="who"><div class="avatar" aria-hidden="true">' + esc((u.name || '?').trim().charAt(0).toUpperCase()) + '</div><div class="t"><b>' + esc(u.name) + '</b><span>' + esc(u.email) + '</span></div><button class="btn btn-ghost btn-sm" id="logout" type="button" aria-label="Log out" title="Log out">' + icon('out', 'width="18" height="18"') + '</button></div></aside><div class="scrim" id="scrim"></div><div class="main"><div class="top"><button class="burger" id="burger" type="button" aria-label="Open menu" aria-expanded="false">' + icon('menu') + '</button><a class="brand" href="#/dashboard">' + LOGO + 'Smart Life Planner</a></div><main id="view" tabindex="-1"></main></div></div>';
    const side = $('#side'), scrim = $('#scrim'), burger = $('#burger');
    const set = open => { side.classList.toggle('open', open); scrim.classList.toggle('on', open); burger.setAttribute('aria-expanded', String(open)); };
    burger.addEventListener('click', () => set(!side.classList.contains('open')));
    scrim.addEventListener('click', () => set(false));
    side.addEventListener('click', e => { if (e.target.closest('a')) set(false); });
    $('#logout').addEventListener('click', async () => {
      try { await api('POST', '/api/logout'); } catch (e) { /* already out */ }
      state.user = null; plan = freshPlan();
      toast('You are logged out.', 'ok');
      go('#/');
    });
  }
  $$('[data-nav]').forEach(a => { if (a.dataset.nav === active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
  return $('#view');
}

/* ------------------------------------------------------------------ public pages */
function pubNav(here) {
  return '<header class="pubnav"><a class="brand" href="#/">' + LOGO + 'Smart Life Planner</a><span class="sp"></span>' +
    (here === 'landing' ? '<a class="plain hide-s" href="#features">Features</a><a class="plain hide-s" href="#how">How it works</a>' : '<a class="plain" href="#/">Home</a>') +
    (here !== 'login' ? '<a class="btn btn-ghost btn-sm" href="#/login">Log in</a>' : '') +
    (here !== 'signup' ? '<a class="btn btn-primary btn-sm" href="#/signup">Sign up</a>' : '') + '</header>';
}
function pubFoot() {
  return '<footer class="foot"><p>Smart Life Planner, Pakistan edition. Built by Maida Javed for the PSEB Python Django Bootcamp. Instructor: Muhammad Waleed Shehbaz.</p><p style="margin-top:8px"><a href="https://github.com/MaidaJaved23" target="_blank" rel="noopener">GitHub profile</a> &nbsp; <a href="https://github.com/MaidaJaved23/python-smart-life-planner" target="_blank" rel="noopener">Repository</a></p></footer>';
}

const METER_PARTS = [['Transport', 24000, 'var(--cy)'], ['Accommodation', 36000, 'var(--vi)'], ['Food and dining', 28000, 'var(--gr)'], ['Activities', 14000, 'var(--pk)']];
function meterScene(wrap, budget) {
  const sub = METER_PARTS.reduce((a, p) => a + p[1], 0);
  const buf = Math.round(sub * 0.05);
  const parts = METER_PARTS.concat([['Emergency allowance (5%)', buf, 'var(--am)']]);
  const total = sub + buf;
  const scale = Math.max(total, budget) * 1.1;
  $$('.seg', wrap).forEach((s, i) => { s.style.width = (parts[i][1] / scale * 100) + '%'; });
  const cap = $('.cap', wrap);
  cap.style.left = (budget / scale * 100) + '%';
  $('.cap em', wrap).textContent = money(budget);
  const v = $('.verdict', wrap);
  const diff = budget - total;
  v.className = 'verdict ' + (diff >= 0 ? 'ok' : 'over');
  v.innerHTML = (diff >= 0 ? icon('check', 'width="22" height="22"') + '<span>Within budget. ' + money(diff) + ' left over.</span>'
    : icon('alert', 'width="22" height="22"') + '<span>Over budget by ' + money(-diff) + '. Alternatives that fit are suggested.</span>');
}

function pageLanding() {
  document.title = 'Smart Life Planner | Pakistan trips and monthly budgets';
  const sub = METER_PARTS.reduce((a, p) => a + p[1], 0), buf = Math.round(sub * 0.05);
  const all = METER_PARTS.concat([['Emergency allowance (5%)', buf, 'var(--am)']]);
  root.innerHTML = pubNav('landing') + '<main id="view" tabindex="-1"><div class="wrap">' +
    '<section class="hero"><div><h1>Know the trip fits your budget before you book it.</h1><p class="lead">Plan journeys across Pakistan, see exactly where the money goes, and get workable alternatives when a plan runs over. Then track the month that follows.</p><div class="cta"><a class="btn btn-primary btn-lg" href="#/signup">Create a free account</a><a class="btn btn-ghost btn-lg" href="#/login">Log in</a></div><p class="fine">Your plans and budgets are saved to your own project files. PDF reports download in one click.</p></div>' +
    '<div class="meter" id="meter" aria-label="Example trip cost meter"><header><b>Example plan</b><span class="muted" style="font-size:14px">4 travellers, 4 days</span></header><p class="route">Costs are example numbers for illustration, not real prices.</p>' +
    '<div class="inline" role="group" aria-label="Try a budget" style="margin-bottom:6px"><button class="chip" type="button" data-b="120000" aria-pressed="true">Budget PKR 120,000</button><button class="chip" type="button" data-b="90000" aria-pressed="false">Budget PKR 90,000</button></div>' +
    '<div class="budget-line"><div class="track">' + all.map(p => '<i class="seg" style="background:' + p[2] + '"></i>').join('') + '</div><div class="cap"><em></em></div></div>' +
    '<ul>' + all.map(p => '<li><i style="background:' + p[2] + '"></i>' + p[0] + '<span>' + money(p[1]) + '</span></li>').join('') + '</ul><div class="verdict ok" aria-live="polite"></div></div></section>' +
    '<section class="sec" id="features"><h2>Two planners, one login</h2><p class="sub">Everything runs on the Python modules you already trust, with checks at every step.</p><div class="feat">' +
    featCard('route', 'var(--cy)', 'Trip feasibility', 'Costs transport, rooms, food and activities by tier, adds a 5% emergency allowance and tells you if the plan is within, exactly within or over budget.') +
    featCard('spark', 'var(--vi)', 'Alternatives that fit', 'When a trip is over budget you get verified options: a higher budget, fewer travellers, a shorter stay or a different destination.') +
    featCard('wallet', 'var(--gr)', 'Monthly budgets', 'Set planned amounts per category, record real expenses and see overspending and your savings rate as you go.') +
    featCard('file', 'var(--pk)', 'PDF reports', 'Confirm a trip or finish a month, then download a clean multi-page PDF with your developer details in the footer.') +
    '</div></section>' +
    '<section class="sec" id="how"><h2>From idea to PDF in four steps</h2><p class="sub">Each step builds on the one before it.</p><div class="flow">' +
    '<div><h3>Create your account</h3><p>Sign up with your name, email and a password of at least 8 characters.</p></div>' +
    '<div><h3>Plan the trip</h3><p>Pick a destination, a travel date from today onward, travellers, nights and a travel tier.</p></div>' +
    '<div><h3>Adjust until it fits</h3><p>Adopt an alternative or change a detail, review the difference, then accept or discard it.</p></div>' +
    '<div><h3>Confirm and download</h3><p>Confirming saves the plan and creates its PDF in your reports folder.</p></div></div></section>' +
    '<div class="cta-band"><div><h2>Ready to plan your next trip?</h2><p class="muted">It takes under a minute to set up.</p></div><a class="btn btn-primary btn-lg" href="#/signup">Create a free account</a></div></div>' + pubFoot() + '</main>';
  const wrap = $('#meter');
  requestAnimationFrame(() => requestAnimationFrame(() => meterScene(wrap, 120000)));
  $$('[data-b]', wrap).forEach(b => b.addEventListener('click', () => {
    $$('[data-b]', wrap).forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    meterScene(wrap, Number(b.dataset.b));
  }));
}
function featCard(ic, color, title, text) {
  return '<div class="panel"><div class="ico" style="color:' + color + ';border-color:' + color + '">' + icon(ic) + '</div><h3>' + title + '</h3><p>' + text + '</p></div>';
}

/* auth */
function pwScore(p) {
  let s = 0;
  if (p.length >= 8) s++;
  if (/[a-z]/.test(p) && /[A-Z]/.test(p)) s++;
  if (/\d/.test(p)) s++;
  if (/[^A-Za-z0-9]/.test(p) || p.length >= 14) s++;
  return p.length ? Math.max(1, s) : 0;
}
function authSide(title) {
  return '<aside class="auth-side"><h2>' + title + '</h2><ul>' +
    '<li>' + icon('route', 'style="color:var(--cy)"') + '<span><b>Trip plans that check themselves.</b> See within, exactly within or over budget in seconds.</span></li>' +
    '<li>' + icon('wallet', 'style="color:var(--gr)"') + '<span><b>Budgets you can trust.</b> Planned against actual, category by category.</span></li>' +
    '<li>' + icon('file', 'style="color:var(--pk)"') + '<span><b>PDF reports on demand.</b> Saved to your reports folder and ready to download.</span></li>' +
    '<li>' + icon('shield', 'style="color:var(--vi)"') + '<span><b>Passwords are hashed.</b> Only a hash is stored, never the password itself.</span></li></ul></aside>';
}
function pageSignup() {
  document.title = 'Sign up | Smart Life Planner';
  root.innerHTML = '<div class="auth"><div class="auth-form"><a class="brand" href="#/">' + LOGO + 'Smart Life Planner</a><h1>Create your account</h1><p class="sub">Start planning trips and budgets in a minute.</p>' +
    '<form id="f" class="stack" novalidate><div class="formerr" role="alert"></div>' +
    fld('name', 'Full name', '<input id="name" name="name" type="text" autocomplete="name" required>') +
    fld('email', 'Email address', '<input id="email" name="email" type="email" autocomplete="email" inputmode="email" required>') +
    fld('password', 'Password', '<div class="pw-wrap"><input id="password" name="password" type="password" autocomplete="new-password" aria-describedby="h-password e-password" required><button type="button" id="tg" aria-label="Show password">Show</button></div><div class="pwmeter" id="pm" data-s="0" aria-hidden="true"><i></i><i></i><i></i><i></i></div>', 'Use at least 8 characters. A mix of letters, numbers and symbols is stronger.') +
    fld('password2', 'Confirm password', '<input id="password2" name="password2" type="password" autocomplete="new-password" required>') +
    '<button class="btn btn-primary btn-lg btn-block" type="submit">Create account</button></form>' +
    '<p class="alt">Already have an account? <a href="#/login">Log in</a></p></div>' + authSide('Plan smarter. Spend with a plan.') + '</div>';
  const f = $('#f');
  $('#tg').addEventListener('click', e => {
    const p = $('#password'), show = p.type === 'password';
    p.type = show ? 'text' : 'password'; $('#password2').type = p.type;
    e.target.textContent = show ? 'Hide' : 'Show'; e.target.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });
  $('#password').addEventListener('input', e => { $('#pm').dataset.s = pwScore(e.target.value); });
  f.addEventListener('submit', async e => {
    e.preventDefault();
    const v = { name: $('#name').value.trim(), email: $('#email').value.trim(), password: $('#password').value, password2: $('#password2').value };
    const errs = {};
    if (v.name.length < 2) errs.name = 'Enter your full name.';
    if (!EMAIL_RE.test(v.email)) errs.email = 'Enter a valid email address, like name@example.com.';
    if (v.password.length < 8) errs.password = 'Password must be at least 8 characters.';
    if (v.password2 !== v.password) errs.password2 = 'The passwords do not match.';
    if (!fieldErrors(f, errs)) return;
    const btn = $('button[type=submit]', f);
    busy(btn, true, 'Creating account');
    try {
      state.user = await api('POST', '/api/signup', { name: v.name, email: v.email, password: v.password });
      toast('Welcome, ' + firstName(state.user.name) + '. Your account is ready.', 'ok');
      const next = state.next; state.next = null;
      go(next || '#/dashboard');
    } catch (err) {
      busy(btn, false);
      if (/email/i.test(err.message)) { setErr($('#email'), err.message); $('#email').focus(); } else $('.formerr', f).textContent = err.message;
    }
  });
}
function pageLogin() {
  document.title = 'Log in | Smart Life Planner';
  root.innerHTML = '<div class="auth"><div class="auth-form"><a class="brand" href="#/">' + LOGO + 'Smart Life Planner</a><h1>Welcome back</h1><p class="sub">Log in to see your trips, budgets and reports.</p>' +
    '<form id="f" class="stack" novalidate><div class="formerr" role="alert"></div>' +
    fld('email', 'Email address', '<input id="email" name="email" type="email" autocomplete="email" inputmode="email" required>') +
    fld('password', 'Password', '<div class="pw-wrap"><input id="password" name="password" type="password" autocomplete="current-password" required><button type="button" id="tg" aria-label="Show password">Show</button></div>') +
    '<button class="btn btn-primary btn-lg btn-block" type="submit">Log in</button></form>' +
    '<p class="alt">New here? <a href="#/signup">Create an account</a></p></div>' + authSide('Pick up where you left off.') + '</div>';
  const f = $('#f');
  $('#tg').addEventListener('click', e => {
    const p = $('#password'), show = p.type === 'password';
    p.type = show ? 'text' : 'password';
    e.target.textContent = show ? 'Hide' : 'Show'; e.target.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });
  f.addEventListener('submit', async e => {
    e.preventDefault();
    const email = $('#email').value.trim(), password = $('#password').value;
    const errs = {};
    if (!EMAIL_RE.test(email)) errs.email = 'Enter the email address you signed up with.';
    if (!password) errs.password = 'Enter your password.';
    if (!fieldErrors(f, errs)) return;
    const btn = $('button[type=submit]', f);
    busy(btn, true, 'Logging in');
    try {
      state.user = await api('POST', '/api/login', { email, password });
      const next = state.next; state.next = null;
      go(next || '#/dashboard');
    } catch (err) {
      busy(btn, false);
      $('.formerr', f).textContent = err.message;
    }
  });
}

/* ------------------------------------------------------------------ shared trip views */
function costPanel(t) {
  const bd = breakdown(t);
  if (!bd) return '<p class="muted">The cost breakdown is not available for this trip.</p>';
  const tot = bd.total || 1;
  return '<div class="stackbar" role="img" aria-label="Share of each cost in the total">' + bd.parts.map(p => '<i title="' + esc(p.label) + '" style="width:' + (p.v / tot * 100) + '%;background:' + p.c + '"></i>').join('') + '</div>' +
    '<div class="tw" style="margin-top:16px"><table><tbody>' +
    bd.parts.map(p => '<tr><td><span class="inline" style="gap:10px"><i style="width:11px;height:11px;border-radius:4px;background:' + p.c + ';display:inline-block"></i>' + esc(p.label) + '</span></td><td class="num">' + money(p.v) + '</td></tr>').join('') +
    '</tbody><tfoot><tr class="tfoot"><td>Total estimated cost</td><td class="num">' + money(bd.total) + '</td></tr>' +
    (bd.perPerson != null ? '<tr class="tfoot"><td>Cost per person</td><td class="num">' + money(bd.perPerson) + '</td></tr>' : '') + '</tfoot></table></div>';
}
function tripKV(t, date) {
  const ret = date && parseISO(date) ? fmtDate(addDays(parseISO(date), Math.max(0, (Number(t.days) || 1) - 1))) : null;
  const bd = breakdown(t);
  const rows = [
    ['Destination', esc(t.destination_name || t.destination || 'n/a')],
    ['Leaving from', esc(t.departure_city || 'n/a')],
    ['Departure', esc(date ? fmtISO(date) : 'Not set')]
  ];
  if (ret) rows.push(['Returning', esc(ret)]);
  rows.push(['Travellers', esc(t.travellers)], ['Duration', esc(t.days) + ' days, ' + esc(t.nights) + ' nights'], ['Travel tier', esc(t.travel_category || 'n/a')], ['Your budget', '<span class="money">' + money(t.budget) + '</span>']);
  if (bd && bd.rooms != null) rows.push(['Rooms needed', esc(bd.rooms)]);
  rows.push(['Trip ID', '<span class="mono">' + esc(t.trip_id) + '</span>']);
  return '<dl class="kv">' + rows.map(r => '<dt>' + r[0] + '</dt><dd>' + r[1] + '</dd>').join('') + '</dl>';
}
function itineraryPanel(t) {
  const it = t.itinerary || t.day_wise_itinerary || t.itinerary_days;
  if (!Array.isArray(it) || !it.length) return '';
  const items = it.map((x, i) => {
    if (typeof x === 'string') return '<li><b>Day ' + (i + 1) + '</b><br>' + esc(x) + '</li>';
    if (!x || typeof x !== 'object') return '';
    const title = x.title || x.day || 'Day ' + (i + 1);
    let body = x.description || x.activities || x.plan || x.details;
    if (Array.isArray(body)) body = body.join(', ');
    if (!body) body = Object.keys(x).filter(k => typeof x[k] === 'string' && x[k] !== title).map(k => x[k]).join('. ');
    return '<li><b>' + esc(typeof title === 'number' ? 'Day ' + title : title) + '</b><br><span class="muted">' + esc(body) + '</span></li>';
  }).join('');
  return '<section class="panel" style="margin-top:20px"><h2>Day-by-day itinerary</h2><ol style="margin:12px 0 0;padding-left:20px;display:grid;gap:12px">' + items + '</ol></section>';
}
function tripDialog(t) {
  const date = tripDates()[t.trip_id];
  openDialog('<h2>' + esc(t.destination_name || 'Trip') + ' ' + verdictBadge(t) + '</h2>' + tripKV(t, date) + '<div class="divider"></div>' + costPanel(t) + '<div class="dfoot"><button class="btn btn-ghost" data-close type="button">Close</button></div>', { wide: true, noFocus: true });
}

/* ------------------------------------------------------------------ dashboard */
async function pageDashboard(view, args, alive) {
  const res = await Promise.allSettled([api('GET', '/api/trips'), api('GET', '/api/budgets'), api('GET', '/api/reports')]);
  if (!alive()) return;
  if (res.every(r => r.status === 'rejected')) throw res[0].reason;
  const trips = res[0].status === 'fulfilled' ? res[0].value : [];
  const budgets = (res[1].status === 'fulfilled' ? res[1].value : []).map(normBudget);
  const reports = res[2].status === 'fulfilled' ? res[2].value : [];
  const last = budgets[budgets.length - 1];
  const recent = trips.slice(-4).reverse();
  view.innerHTML = '<div class="pagehead"><div><h1>Hello, ' + esc(firstName(state.user.name)) + '</h1><p>Here is where your trips, budgets and reports stand today.</p></div><a class="btn btn-primary" href="#/plan">' + icon('plus', 'width="18" height="18"') + 'Plan a trip</a></div>' +
    '<div class="stats">' +
    '<div class="stat" style="--c:var(--cy)"><span>Confirmed trips</span><strong>' + trips.length + '</strong></div>' +
    '<div class="stat" style="--c:var(--vi)"><span>Monthly budgets</span><strong>' + budgets.length + '</strong></div>' +
    '<div class="stat" style="--c:var(--pk)"><span>PDF reports</span><strong>' + reports.length + '</strong></div>' +
    '<div class="stat" style="--c:' + (last && last.remaining < 0 ? 'var(--pk)' : 'var(--gr)') + '"><span>' + (last ? esc(last.month) + (last.remaining < 0 ? ': overspent by' : ': left to spend') : 'Latest budget') + '</span><strong class="money">' + (last ? money(Math.abs(last.remaining)) : 'None yet') + '</strong></div></div>' +
    '<div class="grid2"><section class="panel"><h2>Latest budget</h2>' + (last
      ? '<p class="sub">' + esc(last.month) + ', ' + esc(last.type) + '</p><div class="bar ' + barClass(last.overall) + '" role="img" aria-label="' + Math.round(last.overall * 100) + ' percent of the budget spent"><i style="width:' + Math.min(100, last.overall * 100) + '%"></i></div><div class="inline" style="justify-content:space-between;margin:10px 0 16px"><span class="muted">Spent ' + money(last.totalSpent) + '</span><span class="muted">Available ' + money(last.available) + '</span></div><a class="btn btn-ghost btn-sm" href="#/budgets/' + encodeURIComponent(last.id) + '">Open this budget</a>'
      : '<p class="sub">Set planned amounts for each category, then record expenses as the month goes.</p><a class="btn btn-primary btn-sm" href="#/budgets">Start a budget</a>') + '</section>' +
    '<section class="panel"><h2>Recent trips</h2>' + (recent.length
      ? '<div class="tw" style="margin-top:12px"><table><tbody>' + recent.map(t => { const bd = breakdown(t); return '<tr><td><b>' + esc(t.destination_name) + '</b><br><span class="muted" style="font-size:13.5px">' + esc(t.travellers) + ' travellers, ' + esc(t.days) + 'D/' + esc(t.nights) + 'N</span></td><td class="num">' + (bd ? money(bd.total) : '') + '</td></tr>'; }).join('') + '</tbody></table></div><p style="margin-top:12px"><a href="#/trips">See all trips</a></p>'
      : '<p class="sub">Confirmed plans show up here with their PDF.</p><a class="btn btn-primary btn-sm" href="#/plan">Plan your first trip</a>') + '</section></div>';
}

/* ------------------------------------------------------------------ trip planner */
const freshPlan = () => ({ step: 'form', form: { budget: '', travellers: '2', days: '3', nights: '2', nightsTouched: false, type: 'Any', dest: '', city: 'Islamabad', date: '', cat: 'Standard' }, res: null, confirmed: null });
let plan = freshPlan();
const TYPES = ['Any', 'Mountains', 'Historical Places', 'Lakes & Nature'];
const TIERS = [['Budget', 'Public transport and economy guesthouses'], ['Standard', 'AC coach or saloon and 3-star hotels'], ['Premium', 'Private 4x4 or flights and luxury resorts']];
const CITIES = ['Islamabad', 'Rawalpindi', 'Lahore', 'Karachi', 'Peshawar', 'Quetta', 'Multan', 'Faisalabad', 'Sialkot', 'Hyderabad'];
const typeMatch = (cat, type) => { if (type === 'Any') return true; const n = s => String(s).toLowerCase().replace(/[^a-z]/g, ''); return n(cat).startsWith(n(type).slice(0, 5)); };

async function pagePlan(view, args, alive) {
  if (args[0]) { plan = freshPlan(); plan.form.dest = args[0]; history.replaceState(null, '', '#/plan'); }
  if (plan.step === 'result' && plan.res) return renderResult(view);
  const dests = await getDestinations();
  if (!alive()) return;
  renderForm(view, dests);
}

function planSteps(i) {
  const names = ['Plan', 'Review', 'Confirm'];
  return '<ol class="steps" aria-label="Progress">' + names.map((n, k) => '<li' + (k === i ? ' aria-current="step"' : '') + (k < i ? ' class="done"' : '') + '>' + (k < i ? icon('check', 'width="16" height="16"') : '') + n + '</li>').join('') + '</ol>';
}

function destPick(dests, f) {
  const list = dests.filter(d => typeMatch(d.category, f.type));
  if (!list.length) return '<div class="empty" style="grid-column:1/-1;padding:24px"><p style="margin:0">No destinations match this type. Choose another type.</p></div>';
  return list.map(d => '<label class="choice"><input type="radio" name="destination" value="' + esc(d.id) + '"' + (String(f.dest) === String(d.id) ? ' checked' : '') + '><span><b>' + esc(d.name) + '</b><small>' + esc(d.category) + (d.region ? ', ' + esc(d.region) : '') + '</small></span></label>').join('');
}

function renderForm(view, dests) {
  const f = plan.form, today = todayISO();
  if (!dests.some(d => String(d.id) === String(f.dest))) f.dest = '';
  view.innerHTML = '<div class="pagehead"><div><h1>Plan a trip</h1><p>Tell us the basics. You will see the full cost, a clear verdict and, if the plan runs over, options that fit.</p></div></div>' + planSteps(0) +
    '<form id="pf" class="panel stack" novalidate><div class="formerr" role="alert"></div>' +
    '<div class="row2">' + fld('budget', 'Available budget', '<div class="pre-wrap"><span class="pre">PKR</span><input id="budget" type="text" inputmode="decimal" autocomplete="off" value="' + esc(f.budget) + '" placeholder="75000"></div>', 'The total you can spend for the whole group.') +
    fld('travellers', 'Travellers', '<input id="travellers" type="number" min="1" max="100" step="1" value="' + esc(f.travellers) + '">') + '</div>' +
    '<fieldset><legend class="lbl">Destination type</legend><div class="chips" id="types" style="margin-top:8px">' + TYPES.map(t => '<button type="button" class="chip" data-type="' + esc(t) + '" aria-pressed="' + (f.type === t) + '">' + esc(t) + '</button>').join('') + '</div></fieldset>' +
    '<fieldset id="destination" tabindex="-1"><legend class="lbl">Destination</legend><div class="pick" id="pick" style="margin-top:8px">' + destPick(dests, f) + '</div><div class="err" id="e-destination" role="alert"></div></fieldset>' +
    '<div class="row2">' + fld('city', 'Leaving from', '<input id="city" type="text" list="cities" autocomplete="off" value="' + esc(f.city) + '"><datalist id="cities">' + CITIES.map(c => '<option value="' + c + '">').join('') + '</datalist>') +
    fld('date', 'Departure date', '<input id="date" type="date" min="' + today + '" value="' + esc(f.date) + '">', 'Past dates are disabled. <span id="ret"></span>') + '</div>' +
    '<div class="row2">' + fld('days', 'Days', '<input id="days" type="number" min="1" max="60" step="1" value="' + esc(f.days) + '">') +
    fld('nights', 'Nights', '<input id="nights" type="number" min="0" max="60" step="1" value="' + esc(f.nights) + '">', 'A day trip has 0 nights.') + '</div>' +
    '<fieldset><legend class="lbl">Travel tier</legend><div class="choices" style="margin-top:8px">' + TIERS.map(t => '<label class="choice"><input type="radio" name="cat" value="' + t[0] + '"' + (f.cat === t[0] ? ' checked' : '') + '><span><b>' + t[0] + '</b><small>' + t[1] + '</small></span></label>').join('') + '</div></fieldset>' +
    '<div class="inline"><button class="btn btn-primary btn-lg" type="submit">Check this trip</button><span class="muted" style="font-size:14px">Nothing is saved until you confirm.</span></div></form>';

  const form = $('#pf');
  const dateEl = $('#date');
  const retHint = () => {
    const d = parseISO(dateEl.value), days = num($('#days').value);
    $('#ret').textContent = d && Number.isInteger(days) && days >= 1 ? 'You would return on ' + fmtDate(addDays(d, days - 1)) + '.' : '';
  };
  const sync = () => {
    f.budget = $('#budget').value; f.travellers = $('#travellers').value; f.days = $('#days').value; f.nights = $('#nights').value;
    f.city = $('#city').value; f.date = dateEl.value;
    const c = $('input[name=cat]:checked', form); if (c) f.cat = c.value;
    const d = $('input[name=destination]:checked', form); f.dest = d ? d.value : '';
  };
  form.addEventListener('input', e => {
    if (e.target.id === 'nights') f.nightsTouched = true;
    if (e.target.id === 'days' && !f.nightsTouched) { const d = num(e.target.value); if (Number.isInteger(d) && d >= 1) $('#nights').value = d - 1; }
    sync(); retHint();
    if (e.target.getAttribute && e.target.getAttribute('aria-invalid')) setErr(e.target, '');
  });
  form.addEventListener('change', sync);
  dateEl.addEventListener('focus', () => { dateEl.min = todayISO(); });
  dateEl.addEventListener('change', () => { if (dateEl.value && dateEl.value < todayISO()) { setErr(dateEl, 'Choose a departure date from today onward.'); } else setErr(dateEl, ''); });
  retHint();
  $('#types').addEventListener('click', e => {
    const b = e.target.closest('[data-type]'); if (!b) return;
    sync(); f.type = b.dataset.type;
    $$('#types .chip').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
    if (f.dest && !typeMatch((dests.find(d => String(d.id) === String(f.dest)) || {}).category, f.type)) f.dest = '';
    $('#pick').innerHTML = destPick(dests, f);
  });
  form.addEventListener('submit', async e => {
    e.preventDefault(); sync();
    const errs = validatePlan(f);
    if (!fieldErrors(form, errs)) return;
    const btn = $('button[type=submit]', form);
    busy(btn, true, 'Calculating');
    try {
      const res = await api('POST', '/api/trips/plan', {
        budget: num(f.budget), travellers: num(f.travellers), destination: f.dest, departure_city: f.city.trim() || 'Islamabad',
        days: num(f.days), nights: num(f.nights), travel_category: f.cat, destination_type_pref: f.type, travel_date: f.date
      });
      plan.res = res; plan.step = 'result'; plan.confirmed = null;
      saveTripDate(res.trip.trip_id, f.date);
      window.scrollTo(0, 0);
      renderResult(view);
    } catch (err) {
      busy(btn, false);
      $('.formerr', form).textContent = err.message;
    }
  });
}

function validatePlan(f) {
  const e = {};
  const b = num(f.budget);
  if (String(f.budget).trim() === '' || !isFinite(b)) e.budget = 'Enter your budget as a number, like 75000.';
  else if (b <= 0) e.budget = 'Budget must be greater than zero.';
  const t = num(f.travellers);
  if (!Number.isInteger(t) || t < 1 || t > 100) e.travellers = 'Enter a whole number from 1 to 100.';
  if (!f.dest) e.destination = 'Choose a destination.';
  const days = num(f.days), nights = num(f.nights);
  if (!Number.isInteger(days) || days < 1 || days > 60) e.days = 'Enter whole days from 1 to 60.';
  if (!Number.isInteger(nights) || nights < 0 || nights > 60) e.nights = 'Enter whole nights from 0 to 60.';
  else if (Number.isInteger(days) && nights > days) e.nights = 'Nights (' + nights + ') cannot exceed days (' + days + ').';
  if (!f.date) e.date = 'Choose a departure date.';
  else if (!parseISO(f.date)) e.date = 'Enter a valid date.';
  else if (f.date < todayISO()) e.date = 'Choose a departure date from today onward.';
  return e;
}

function renderResult(view) {
  const r = plan.res, t = r.trip || {}, vd = verdictOf(t, r.status), V = VERDICT[vd], bd = breakdown(t);
  const date = plan.form.date || tripDates()[t.trip_id];
  const diff = bd ? Number(t.budget) - bd.total : null;
  const msg = r.message || (diff == null ? '' : vd === 'over' ? 'This plan is short by ' + money(-diff) + '.' : vd === 'exact' ? 'The total matches your budget to the paisa.' : 'You would have ' + money(diff) + ' left over.');
  const confirmed = plan.confirmed;
  const alts = Array.isArray(r.alternatives) ? r.alternatives : [];
  view.innerHTML = '<div class="pagehead"><div><h1>' + esc(t.destination_name || 'Your trip') + '</h1><p>' + esc(t.travellers) + ' travellers, ' + esc(t.days) + ' days and ' + esc(t.nights) + ' nights, ' + esc(t.travel_category) + ' tier.</p></div></div>' + planSteps(confirmed ? 2 : 1) +
    '<div class="verdict-box ' + vd + '" role="status">' + icon(V.icon) + '<div><h2>' + V.text + '</h2><p>' + esc(msg) + '</p></div></div>' +
    (confirmed ? '<section class="panel tint-gr pdfbox" style="margin-bottom:20px"><div><h2>Trip saved</h2><p class="muted">' + (confirmed.file ? 'Your PDF report is ready: <span class="mono">' + esc(confirmed.file) + '</span>' : 'The trip is saved, but its PDF could not be created. ' + esc(confirmed.error || '')) + '</p></div><div class="inline">' +
      (confirmed.file ? '<button class="btn btn-green" data-act="download" type="button">' + icon('down', 'width="18" height="18"') + 'Download PDF</button>' : '<button class="btn btn-green" data-act="makepdf" type="button">Create PDF</button>') +
      '<a class="btn btn-ghost" href="#/trips">My trips</a><button class="btn btn-ghost" data-act="restart" type="button">Plan another trip</button></div></section>' : '') +
    '<div class="grid2"><section class="panel"><h2>Where the money goes</h2><p class="sub">Your budget is ' + money(t.budget) + '.</p>' + costPanel(t) + '</section>' +
    '<section class="panel"><h2>Trip details</h2><p class="sub">Review before you confirm.</p>' + tripKV(t, date) +
    (confirmed ? '' : '<div class="divider"></div><div class="inline">' +
      (vd === 'over' ? '<button class="btn btn-green" type="button" disabled title="Make the plan fit first">Confirm and save</button>' : '<button class="btn btn-green" data-act="confirm" type="button">Confirm and save</button>') +
      '<button class="btn btn-ghost" data-act="modify" type="button">Change details</button><button class="btn btn-ghost" data-act="restart" type="button">Start over</button></div>' +
      (vd === 'over' ? '<p class="hint" style="margin-top:10px">Adopt one of the options below or change the details, then confirm.</p>' : '<p class="hint" style="margin-top:10px">Confirming saves the plan and creates its PDF.</p>')) + '</section></div>' +
    (vd === 'over' && !confirmed ? (r.shortage ? '<section class="panel tint-am" style="margin-top:20px"><h2>Why it runs over</h2><pre class="shortage" style="margin:12px 0 0">' + esc(r.shortage) + '</pre></section>' : '') +
      '<section style="margin-top:20px"><div class="panel-head"><div><h2 style="font-size:22px">Options that fit your budget</h2><p class="muted">Each option was recalculated and checked against its own budget.</p></div></div>' +
      (alts.length ? '<div class="grid3">' + alts.map((a, i) => altCard(a, i)).join('') + '</div>' : '<div class="empty"><h3>No automatic option fits</h3><p>Try a higher budget, fewer travellers or a shorter stay with Change details.</p></div>') + '</section>' : '') +
    itineraryPanel(t);

  view.onclick = async e => {
    const b = e.target.closest('[data-act]'); if (!b) return;
    const act = b.dataset.act;
    if (act === 'restart') { plan = freshPlan(); render(); }
    else if (act === 'download') download(plan.confirmed.file);
    else if (act === 'modify') modifyDialog(t, view);
    else if (act === 'adopt') {
      busy(b, true, 'Adopting');
      try {
        const res = await api('POST', '/api/trips/' + encodeURIComponent(t.trip_id) + '/adopt/' + b.dataset.rank);
        plan.res = res; saveTripDate(res.trip.trip_id, plan.form.date);
        toast('Option adopted. Review the new plan below.', 'ok'); window.scrollTo(0, 0); renderResult(view);
      } catch (err) { busy(b, false); toast(err.message, 'bad'); }
    } else if (act === 'confirm') {
      busy(b, true, 'Saving');
      try {
        const res = await api('POST', '/api/trips/' + encodeURIComponent(t.trip_id) + '/confirm');
        plan.confirmed = { file: res.file || null, error: res.pdf_error || '' };
        saveTripDate(t.trip_id, plan.form.date);
        toast(res.file ? 'Trip saved and PDF created.' : 'Trip saved. The PDF needs another try.', res.file ? 'ok' : 'bad');
        window.scrollTo(0, 0); renderResult(view);
      } catch (err) { busy(b, false); toast(err.message, 'bad'); }
    } else if (act === 'makepdf') {
      busy(b, true, 'Creating PDF');
      try {
        const res = await api('POST', '/api/trips/' + encodeURIComponent(t.trip_id) + '/pdf');
        plan.confirmed = { file: res.file }; renderResult(view); toast('PDF created.', 'ok');
      } catch (err) { busy(b, false); toast(err.message, 'bad'); }
    }
  };
}

function altCard(a, i) {
  const mt = a.modified_trip || {};
  const bd = breakdown(mt);
  const title = a.title || 'Option ' + (i + 1);
  const desc = pick(a, /desc|detail|summary|explan|message/i, 'string');
  const fits = bd && Number(mt.budget) >= bd.total - 0.005;
  return '<article class="panel alt-card tint-cy"><span class="rank">Option ' + (i + 1) + '</span><h3>' + esc(title) + '</h3>' + (desc ? '<p class="muted" style="font-size:14.5px">' + esc(desc) + '</p>' : '') +
    '<dl class="kv" style="font-size:14px"><dt>Destination</dt><dd>' + esc(mt.destination_name || '') + '</dd><dt>Travellers</dt><dd>' + esc(mt.travellers) + '</dd><dt>Duration</dt><dd>' + esc(mt.days) + 'D/' + esc(mt.nights) + 'N</dd><dt>Budget</dt><dd class="money">' + money(mt.budget) + '</dd><dt>New total</dt><dd class="money">' + (bd ? money(bd.total) : 'n/a') + '</dd></dl>' +
    (fits ? '<span class="badge ok" style="align-self:flex-start">Fits the budget</span>' : '') +
    '<button class="btn btn-primary btn-block" data-act="adopt" data-rank="' + (i + 1) + '" type="button" style="margin-top:auto">Adopt this option</button></article>';
}

async function modifyDialog(t, view) {
  let dests = [];
  try { dests = await getDestinations(); } catch (e) { /* select falls back to current */ }
  const cur = t.destination_id != null ? t.destination_id : '';
  openDialog('<h2>Change trip details</h2><p class="muted" style="margin-bottom:16px">Change only what you need. You will review the difference before anything is applied.</p>' +
    '<form id="mf" class="stack" novalidate><div class="formerr" role="alert"></div><div class="row2">' +
    fld('m-budget', 'Budget (PKR)', '<input id="m-budget" type="text" inputmode="decimal" value="' + esc(t.budget) + '">') +
    fld('m-travellers', 'Travellers', '<input id="m-travellers" type="number" min="1" max="100" value="' + esc(t.travellers) + '">') + '</div>' +
    fld('m-dest', 'Destination', '<select id="m-dest">' + (dests.length ? dests.map(d => '<option value="' + esc(d.id) + '"' + (String(d.id) === String(cur) || d.name === t.destination_name ? ' selected' : '') + '>' + esc(d.name) + '</option>').join('') : '<option value="">' + esc(t.destination_name) + '</option>') + '</select>') +
    '<div class="row2">' + fld('m-days', 'Days', '<input id="m-days" type="number" min="1" max="60" value="' + esc(t.days) + '">') + fld('m-nights', 'Nights', '<input id="m-nights" type="number" min="0" max="60" value="' + esc(t.nights) + '">') + '</div>' +
    fld('m-cat', 'Travel tier', '<select id="m-cat">' + TIERS.map(x => '<option' + (x[0] === t.travel_category ? ' selected' : '') + '>' + x[0] + '</option>').join('') + '</select>') +
    '<div class="dfoot"><button class="btn btn-ghost" data-close type="button">Cancel</button><button class="btn btn-primary" type="submit">Review changes</button></div></form>', { wide: false });
  const form = $('#mf', dlg);
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const errs = {};
    const b = num($('#m-budget').value), tr = num($('#m-travellers').value), days = num($('#m-days').value), nights = num($('#m-nights').value);
    if (!isFinite(b) || b <= 0) errs['m-budget'] = 'Enter a budget greater than zero.';
    if (!Number.isInteger(tr) || tr < 1 || tr > 100) errs['m-travellers'] = 'Enter a whole number from 1 to 100.';
    if (!Number.isInteger(days) || days < 1 || days > 60) errs['m-days'] = 'Enter whole days from 1 to 60.';
    if (!Number.isInteger(nights) || nights < 0 || nights > 60) errs['m-nights'] = 'Enter whole nights from 0 to 60.';
    else if (Number.isInteger(days) && nights > days) errs['m-nights'] = 'Nights cannot exceed days.';
    if (!fieldErrors(form, errs)) return;
    const upd = {};
    if (b !== Number(t.budget)) upd.budget = b;
    if (tr !== Number(t.travellers)) upd.travellers = tr;
    const dv = $('#m-dest').value;
    if (dv && String(dv) !== String(cur)) upd.destination = dv;
    if (days !== Number(t.days) || nights !== Number(t.nights)) { upd.days = days; upd.nights = nights; }
    if ($('#m-cat').value !== t.travel_category) upd.travel_category = $('#m-cat').value;
    if (!Object.keys(upd).length) { $('.formerr', form).textContent = 'Nothing was changed. Edit a value to continue.'; return; }
    const btn = $('button[type=submit]', form);
    busy(btn, true, 'Recalculating');
    try {
      const res = await api('POST', '/api/trips/' + encodeURIComponent(t.trip_id) + '/modify', upd);
      reviewDialog(t, res, view);
    } catch (err) { busy(btn, false); $('.formerr', form).textContent = err.message; }
  });
}

function reviewDialog(cur, res, view) {
  const a = res.current || cur, c = res.candidate || {};
  const ba = breakdown(a), bc = breakdown(c);
  const rows = [
    ['Destination', a.destination_name, c.destination_name],
    ['Budget', money(a.budget), money(c.budget)],
    ['Travellers', a.travellers, c.travellers],
    ['Duration', a.days + 'D/' + a.nights + 'N', c.days + 'D/' + c.nights + 'N'],
    ['Travel tier', a.travel_category, c.travel_category],
    ['Total cost', ba ? money(ba.total) : 'n/a', bc ? money(bc.total) : 'n/a'],
    ['Status', VERDICT[verdictOf(a)].text, VERDICT[verdictOf(c, res.status)].text]
  ];
  let decided = false;
  openDialog('<h2>Review the changes</h2><div class="tw"><table class="diff"><thead><tr><th>Detail</th><th>Current</th><th>New</th></tr></thead><tbody>' +
    rows.map(r => '<tr><td>' + r[0] + '</td><td class="old">' + esc(r[1]) + '</td><td class="' + (String(r[1]) !== String(r[2]) ? 'chg' : '') + '">' + esc(r[2]) + '</td></tr>').join('') + '</tbody></table></div>' +
    (res.message ? '<p class="muted" style="margin-top:12px">' + esc(res.message) + '</p>' : '') +
    '<div class="dfoot"><button class="btn btn-ghost" id="rv-no" type="button">Keep current plan</button><button class="btn btn-primary" id="rv-yes" type="button">Accept changes</button></div>', { wide: true, noFocus: true,
      onclose: () => { if (!decided) api('POST', '/api/trips/' + encodeURIComponent(cur.trip_id) + '/cancel').catch(() => {}); } });
  $('#rv-no', dlg).addEventListener('click', () => { closeDialog(); api('POST', '/api/trips/' + encodeURIComponent(cur.trip_id) + '/cancel').catch(() => {}); toast('No changes made. Your current plan is unchanged.'); });
  $('#rv-yes', dlg).addEventListener('click', async e => {
    busy(e.currentTarget, true, 'Applying');
    try {
      const out = await api('POST', '/api/trips/' + encodeURIComponent(cur.trip_id) + '/accept');
      decided = true; plan.res = out; plan.confirmed = null;
      saveTripDate(out.trip.trip_id, plan.form.date || tripDates()[cur.trip_id]);
      closeDialog(); toast('Changes applied.', 'ok'); window.scrollTo(0, 0); renderResult(view);
    } catch (err) { busy(e.currentTarget, false); toast(err.message, 'bad'); }
  });
}

/* ------------------------------------------------------------------ my trips */
async function pageTrips(view, args, alive) {
  const trips = await api('GET', '/api/trips');
  if (!alive()) return;
  const dates = tripDates();
  view.innerHTML = '<div class="pagehead"><div><h1>My trips</h1><p>Every plan you confirmed, with its cost and PDF.</p></div><a class="btn btn-primary" href="#/plan">' + icon('plus', 'width="18" height="18"') + 'Plan a trip</a></div>' +
    (trips.length ? '<div class="tw"><table><thead><tr><th>Trip</th><th>Departure</th><th>Travellers</th><th>Duration</th><th>Tier</th><th class="num">Total cost</th><th>Status</th><th><span class="sr">Actions</span></th></tr></thead><tbody>' +
      trips.map((t, i) => { const bd = breakdown(t); return '<tr><td><b>' + esc(t.destination_name) + '</b><br><span class="mono muted" style="font-size:12.5px">' + esc(t.trip_id) + '</span></td><td class="nowrap">' + (dates[t.trip_id] ? esc(fmtISO(dates[t.trip_id])) : '<span class="muted">Not recorded</span>') + '</td><td>' + esc(t.travellers) + '</td><td class="nowrap">' + esc(t.days) + 'D/' + esc(t.nights) + 'N</td><td>' + esc(t.travel_category) + '</td><td class="num">' + (bd ? money(bd.total) : 'n/a') + '</td><td>' + verdictBadge(t) + '</td><td><div class="acts"><button class="btn btn-ghost btn-sm" data-view="' + i + '" type="button">View</button><button class="btn btn-ghost btn-sm" data-pdf="' + i + '" type="button">PDF</button></div></td></tr>'; }).join('') + '</tbody></table></div>'
      : '<div class="empty">' + icon('bag') + '<h3>No confirmed trips yet</h3><p>Plan a trip and confirm it. It will appear here with a PDF you can download.</p><a class="btn btn-primary" href="#/plan">Plan your first trip</a></div>');
  view.onclick = async e => {
    const v = e.target.closest('[data-view]'), p = e.target.closest('[data-pdf]');
    if (v) tripDialog(trips[+v.dataset.view]);
    if (p) {
      const t = trips[+p.dataset.pdf];
      busy(p, true, 'PDF');
      try { const res = await api('POST', '/api/trips/' + encodeURIComponent(t.trip_id) + '/pdf'); busy(p, false); await download(res.file); }
      catch (err) { busy(p, false); toast(err.message, 'bad'); }
    }
  };
}

/* ------------------------------------------------------------------ destinations */
async function pageDestinations(view, args, alive) {
  const dests = await getDestinations();
  if (!alive()) return;
  let type = 'Any', q = '';
  view.innerHTML = '<div class="pagehead"><div><h1>Destinations</h1><p>Costs are seasonal estimates from data/destinations.json, not guaranteed market rates.</p></div></div>' +
    '<div class="inline" style="margin-bottom:20px;justify-content:space-between"><div class="chips" id="dt">' + TYPES.map(t => '<button type="button" class="chip" data-type="' + esc(t) + '" aria-pressed="' + (t === 'Any') + '">' + esc(t) + '</button>').join('') + '</div><div style="min-width:240px;flex:1;max-width:340px"><label class="sr" for="dq">Search destinations</label><input id="dq" type="search" placeholder="Search by name or region"></div></div><div id="dl" class="grid3"></div>';
  const draw = () => {
    const list = dests.filter(d => typeMatch(d.category, type) && (d.name + ' ' + d.region + ' ' + d.description).toLowerCase().includes(q));
    $('#dl').innerHTML = list.length ? list.map(d =>
      '<article class="panel dest"><div><h3>' + esc(d.name) + '</h3><div class="tags" style="margin-top:8px"><span class="badge exact">' + esc(d.category) + '</span>' + (d.region ? '<span class="badge mute">' + esc(d.region) + '</span>' : '') + '</div></div>' +
      (d.description ? '<p class="d">' + esc(d.description) + '</p>' : '') +
      '<dl>' + (d.transport != null ? '<dt>Transport per person</dt><dd>' + money(d.transport) + '</dd>' : '') + (d.hotel != null ? '<dt>Room per night</dt><dd>' + money(d.hotel) + '</dd>' : '') + (d.food != null ? '<dt>Food per person per day</dt><dd>' + money(d.food) + '</dd>' : '') + (d.activities != null ? '<dt>Activities per person per day</dt><dd>' + money(d.activities) + '</dd>' : '') + (d.capacity != null ? '<dt>Room capacity</dt><dd>' + d.capacity + ' people</dd>' : '') + '</dl>' +
      (d.attractions.length ? '<p class="att">Highlights: ' + esc(d.attractions.slice(0, 4).join(', ')) + '</p>' : '') +
      '<a class="btn btn-ghost go" href="#/plan/' + encodeURIComponent(d.id) + '">Plan a trip here</a></article>').join('')
      : '<div class="empty" style="grid-column:1/-1"><h3>No destinations found</h3><p>Try a different type or clear the search.</p></div>';
  };
  draw();
  $('#dt').addEventListener('click', e => { const b = e.target.closest('[data-type]'); if (!b) return; type = b.dataset.type; $$('#dt .chip').forEach(x => x.setAttribute('aria-pressed', String(x === b))); draw(); });
  $('#dq').addEventListener('input', e => { q = e.target.value.trim().toLowerCase(); draw(); });
}

/* ------------------------------------------------------------------ budgets */
const PALETTE = ['#22D3EE', '#9B7BFF', '#2DF5A8', '#FF4D8D', '#FFC857', '#5B8CFF', '#FF8A5B', '#7EE0C3'];
const monthLabel = ym => { const m = /^(\d{4})-(\d{2})$/.exec(ym || ''); return m ? new Date(+m[1], +m[2] - 1, 1).toLocaleString('en-US', { month: 'long', year: 'numeric' }) : ''; };

async function pageBudgets(view, args, alive) {
  if (args[0]) return pageBudgetDetail(view, args[0], alive);
  const list = (await api('GET', '/api/budgets')).map(normBudget);
  if (!alive()) return;
  view.innerHTML = '<div class="pagehead"><div><h1>Budgets</h1><p>One budget per month. Plan each category, then record what you actually spend.</p></div><button class="btn btn-primary" id="nb" type="button">' + icon('plus', 'width="18" height="18"') + 'New budget</button></div>' +
    (list.length ? '<div class="grid3">' + list.slice().reverse().map(b =>
      '<a class="panel" style="text-decoration:none;color:inherit;display:block" href="#/budgets/' + encodeURIComponent(b.id) + '"><div class="inline" style="justify-content:space-between"><h2 style="margin:0">' + esc(b.month) + '</h2><span class="badge ' + (b.remaining < 0 ? 'bad' : 'ok') + '">' + (b.remaining < 0 ? 'Overspent' : 'On track') + '</span></div><p class="muted" style="margin:4px 0 16px">' + esc(b.type) + '</p><div class="bar ' + barClass(b.overall) + '"><i style="width:' + Math.min(100, b.overall * 100) + '%"></i></div><div class="inline" style="justify-content:space-between;margin-top:10px;font-size:14px"><span class="muted">Spent <span class="money">' + money(b.totalSpent) + '</span></span><span class="muted">of <span class="money">' + money(b.available) + '</span></span></div></a>').join('') + '</div>'
      : '<div class="empty">' + icon('wallet') + '<h3>No budgets yet</h3><p>Create a budget for this month, set planned amounts and start recording expenses.</p><button class="btn btn-primary" id="nb2" type="button">Create your first budget</button></div>');
  const open = () => budgetDialog();
  const a = $('#nb'); if (a) a.addEventListener('click', open);
  const c = $('#nb2'); if (c) c.addEventListener('click', open);
}

function budgetDialog() {
  const now = new Date(), ym = now.getFullYear() + '-' + pad(now.getMonth() + 1);
  openDialog('<h2>New monthly budget</h2><form id="bf" class="stack" novalidate><div class="formerr" role="alert"></div>' +
    fld('b-month', 'Month', '<input id="b-month" type="month" value="' + ym + '">') +
    '<fieldset><legend class="lbl">Budget type</legend><div class="choices" style="margin-top:8px"><label class="choice"><input type="radio" name="btype" value="Home & Kitchen" checked><span><b>Home and kitchen</b><small>Grocery, utilities, rent, medical and more</small></span></label><label class="choice"><input type="radio" name="btype" value="Personal Finance"><span><b>Personal finance</b><small>Dining, gym, shopping, education and more</small></span></label></div></fieldset>' +
    fld('b-total', 'Total available', '<div class="pre-wrap"><span class="pre">PKR</span><input id="b-total" type="text" inputmode="decimal" placeholder="150000" autocomplete="off"></div>', 'You can set planned amounts for each category on the next screen.') +
    '<div class="dfoot"><button class="btn btn-ghost" data-close type="button">Cancel</button><button class="btn btn-primary" type="submit">Create budget</button></div></form>');
  const form = $('#bf', dlg);
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const errs = {};
    const month = monthLabel($('#b-month').value), total = num($('#b-total').value);
    if (!month) errs['b-month'] = 'Choose a month.';
    if (!isFinite(total) || total <= 0) errs['b-total'] = 'Enter an amount greater than zero, like 150000.';
    if (!fieldErrors(form, errs)) return;
    const btn = $('button[type=submit]', form);
    busy(btn, true, 'Creating');
    try {
      const v = await api('POST', '/api/budgets', { month, budget_type: $('input[name=btype]:checked', form).value, total_available: total });
      const b = normBudget(v);
      closeDialog(); toast('Budget created for ' + month + '.', 'ok');
      go('#/budgets/' + encodeURIComponent(b.id));
    } catch (err) { busy(btn, false); $('.formerr', form).textContent = err.message; }
  });
}

async function pageBudgetDetail(view, id, alive) {
  const raw = await api('GET', '/api/budgets/' + encodeURIComponent(id));
  if (!alive()) return;
  let filter = '';
  const draw = () => {
    const b = normBudget(raw.cur || raw);
    document.title = b.month + ' budget | Smart Life Planner';
    const over = b.remaining < 0;
    const spentRows = b.rows.filter(r => r.spent > 0);
    const exps = b.expenses.filter(e => !filter || e.category === filter).slice().sort((x, y) => String(y.date).localeCompare(String(x.date)));
    const R = 70, C = 2 * Math.PI * R;
    let off = 0;
    const arcs = spentRows.map((r, i) => { const len = (r.spent / b.totalSpent) * C; const s = '<circle cx="88" cy="88" r="' + R + '" fill="none" stroke="' + PALETTE[i % PALETTE.length] + '" stroke-width="22" stroke-dasharray="' + len + ' ' + (C - len) + '" stroke-dashoffset="' + (-off) + '" transform="rotate(-90 88 88)"/>'; off += len; return s; }).join('');
    view.innerHTML = '<div class="crumb"><a href="#/budgets">Budgets</a> / ' + esc(b.month) + '</div><div class="pagehead"><div><h1>' + esc(b.month) + '</h1><p>' + esc(b.type) + '. <span class="mono muted" style="font-size:13px">' + esc(b.id) + '</span></p></div><div class="inline"><button class="btn btn-ghost" id="addexp" type="button">' + icon('plus', 'width="18" height="18"') + 'Record expense</button><button class="btn btn-green" id="bpdf" type="button">' + icon('down', 'width="18" height="18"') + 'Create PDF report</button></div></div>' +
      (over ? '<div class="verdict-box over" role="status">' + icon('alert') + '<div><h2>You are over budget</h2><p>Spending is ' + money(-b.remaining) + ' above the ' + money(b.available) + ' available.</p></div></div>' : '') +
      '<div class="stats"><div class="stat" style="--c:var(--cy)"><span>Available</span><strong class="money">' + money(b.available) + '</strong></div><div class="stat" style="--c:var(--vi)"><span>Planned</span><strong class="money">' + money(b.totalPlanned) + '</strong><small>' + (b.totalPlanned > b.available ? 'Plans exceed what is available' : 'across ' + b.rows.filter(r => r.planned > 0).length + (b.rows.filter(r => r.planned > 0).length === 1 ? ' category' : ' categories')) + '</small></div><div class="stat" style="--c:var(--am)"><span>Spent</span><strong class="money">' + money(b.totalSpent) + '</strong></div><div class="stat" style="--c:' + (over ? 'var(--pk)' : 'var(--gr)') + '"><span>' + (over ? 'Overspent by' : 'Left to spend') + '</span><strong class="money">' + money(Math.abs(b.remaining)) + '</strong><small>Savings rate ' + b.savingsPct.toFixed(1) + '%</small></div></div>' +
      '<div class="bar ' + barClass(b.overall) + '" style="margin:-4px 0 24px;height:12px" role="img" aria-label="' + Math.round(b.overall * 100) + ' percent of the available amount is spent"><i style="width:' + Math.min(100, b.overall * 100) + '%"></i></div>' +
      '<div class="stack" style="gap:20px"><section class="panel"><div class="panel-head"><div><h2>Categories</h2><p class="muted" style="font-size:14.5px">Edit a planned amount and press Enter to save.</p></div></div>' +
      (b.rows.length ? '<div class="tw"><table><thead><tr><th>Category</th><th class="num">Planned</th><th class="num">Spent</th><th>Progress</th><th><span class="sr">Remove</span></th></tr></thead><tbody>' +
        b.rows.map((r, ri) => { const ratio = r.planned > 0 ? r.spent / r.planned : (r.spent > 0 ? 2 : 0); return '<tr><td>' + esc(r.name) + (r.spent > r.planned ? ' <span class="badge bad" style="margin-left:6px">Over plan</span>' : '') + '</td><td class="num"><label class="sr" for="p-' + ri + '">Planned amount for ' + esc(r.name) + '</label><input class="inl" type="text" inputmode="decimal" id="p-' + ri + '" data-cat="' + esc(r.name) + '" value="' + r.planned + '"' + (r.inPlan ? '' : ' disabled') + '></td><td class="num">' + money(r.spent) + '</td><td style="min-width:110px"><div class="bar ' + barClass(ratio) + '"><i style="width:' + Math.min(100, ratio * 100) + '%"></i></div></td><td>' + (r.inPlan ? '<button class="btn btn-ghost btn-sm" data-rmcat="' + esc(r.name) + '" type="button" aria-label="Remove ' + esc(r.name) + '">Remove</button>' : '') + '</td></tr>'; }).join('') + '</tbody></table></div>'
        : '<div class="empty" style="padding:24px"><p style="margin:0">No categories yet. Add one below.</p></div>') +
      '<form id="cf" class="inline" style="margin-top:16px;align-items:flex-start" novalidate><div style="flex:1;min-width:150px">' + fld('c-name', '<span class="sr">Category name</span>', '<input id="c-name" type="text" placeholder="New category name" maxlength="60">') + '</div><div style="width:150px">' + fld('c-plan', '<span class="sr">Planned amount</span>', '<input id="c-plan" type="text" inputmode="decimal" placeholder="Planned PKR">') + '</div><button class="btn btn-ghost" type="submit" style="margin-top:2px">Add category</button></form></section>' +
      '<section class="panel"><h2>Where the money went</h2><p class="muted" style="font-size:14.5px;margin-bottom:14px">Share of spending by category.</p>' +
      (spentRows.length ? '<div class="donut"><svg viewBox="0 0 176 176" role="img" aria-label="Spending by category">' + arcs + '<text x="88" y="84" text-anchor="middle" fill="#98A4CC" font-size="12">Spent</text><text x="88" y="104" text-anchor="middle" fill="#E8EEFF" font-size="15" font-weight="700" font-family="JetBrains Mono, monospace">' + Math.round(b.overall * 100) + '%</text></svg><div class="legend">' + spentRows.map((r, i) => '<div><i style="background:' + PALETTE[i % PALETTE.length] + '"></i>' + esc(r.name) + '<span>' + money(r.spent) + '</span></div>').join('') + '</div></div>'
        : '<div class="empty" style="padding:24px"><p style="margin:0">Record an expense to see the split.</p></div>') + '</section></div>' +
      '<section class="panel" style="margin-top:20px"><div class="panel-head"><div><h2>Expenses</h2><p class="muted" style="font-size:14.5px">' + b.expenses.length + ' recorded</p></div><div style="min-width:200px"><label class="sr" for="ef">Filter by category</label><select id="ef"><option value="">All categories</option>' + b.rows.map(r => '<option' + (filter === r.name ? ' selected' : '') + ' value="' + esc(r.name) + '">' + esc(r.name) + '</option>').join('') + '</select></div></div>' +
      (exps.length ? '<div class="tw"><table><thead><tr><th>Date</th><th>Category</th><th>Description</th><th class="num">Amount</th><th><span class="sr">Actions</span></th></tr></thead><tbody>' + exps.map(e => '<tr><td class="nowrap">' + esc(e.date) + '</td><td>' + esc(e.category) + '</td><td>' + esc(e.description || '') + '</td><td class="num">' + money(e.amount) + '</td><td><div class="acts"><button class="btn btn-ghost btn-sm" data-ed="' + esc(e.id) + '" type="button">Edit</button><button class="btn btn-danger btn-sm" data-del="' + esc(e.id) + '" type="button">Delete</button></div></td></tr>').join('') + '</tbody></table></div>'
        : '<div class="empty" style="padding:28px">' + icon('list') + '<h3>' + (filter ? 'No expenses in this category' : 'No expenses yet') + '</h3><p>' + (filter ? 'Choose another category or record a new expense.' : 'Record your first expense to start tracking.') + '</p><button class="btn btn-primary" id="addexp2" type="button">Record expense</button></div>') + '</section>';
    bind(b);
  };
  const keepScroll = fn => { const y = window.scrollY; fn(); window.scrollTo(0, y); };
  const update = v => { raw.cur = v; keepScroll(draw); };
  const bind = b => {
    const openAdd = () => expenseDialog(b, null, update);
    $('#addexp').addEventListener('click', openAdd);
    const a2 = $('#addexp2'); if (a2) a2.addEventListener('click', openAdd);
    $('#ef').addEventListener('change', e => { filter = e.target.value; keepScroll(draw); });
    $('#bpdf').addEventListener('click', async e => {
      const btn = e.currentTarget; busy(btn, true, 'Creating PDF');
      try { const res = await api('POST', '/api/budgets/' + encodeURIComponent(b.id) + '/pdf'); busy(btn, false); toast('PDF report created.', 'ok'); await download(res.file); }
      catch (err) { busy(btn, false); toast(err.message, 'bad'); }
    });
    $$('input[data-cat]', view).forEach(inp => {
      const save = async () => {
        const name = inp.dataset.cat, row = b.rows.find(r => r.name === name), v = num(inp.value);
        if (!isFinite(v) || v < 0) { inp.setAttribute('aria-invalid', 'true'); toast('Enter a planned amount of 0 or more.', 'bad'); return; }
        inp.removeAttribute('aria-invalid');
        if (row && v === row.planned) return;
        try { update(await api('PUT', '/api/budgets/' + encodeURIComponent(b.id) + '/categories/' + encodeURIComponent(name), { planned: v })); toast('Planned amount for ' + name + ' saved.', 'ok'); }
        catch (err) { toast(err.message, 'bad'); }
      };
      inp.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); inp.blur(); } });
      inp.addEventListener('change', save);
    });
    $$('[data-rmcat]', view).forEach(btn => btn.addEventListener('click', async () => {
      const name = btn.dataset.rmcat;
      if (!await confirmDialog('Remove ' + name + '?', 'The category and its planned amount are removed from this budget.', 'Remove category', true)) return;
      try { update(await api('DELETE', '/api/budgets/' + encodeURIComponent(b.id) + '/categories/' + encodeURIComponent(name))); toast(name + ' removed.', 'ok'); }
      catch (err) { toast(err.message, 'bad'); }
    }));
    $('#cf').addEventListener('submit', async e => {
      e.preventDefault();
      const f = e.currentTarget, name = $('#c-name').value.trim(), planned = $('#c-plan').value.trim() === '' ? 0 : num($('#c-plan').value);
      const errs = {};
      if (!name) errs['c-name'] = 'Enter a category name.';
      else if (b.rows.some(r => r.name.toLowerCase() === name.toLowerCase())) errs['c-name'] = 'This category already exists.';
      if (!isFinite(planned) || planned < 0) errs['c-plan'] = 'Enter 0 or more.';
      if (!fieldErrors(f, errs)) return;
      try { update(await api('POST', '/api/budgets/' + encodeURIComponent(b.id) + '/categories', { name, planned })); toast('Category ' + name + ' added.', 'ok'); }
      catch (err) { setErr($('#c-name'), err.message); }
    });
    $$('[data-ed]', view).forEach(btn => btn.addEventListener('click', () => expenseDialog(b, b.expenses.find(x => String(x.id) === btn.dataset.ed), update)));
    $$('[data-del]', view).forEach(btn => btn.addEventListener('click', async () => {
      const ex = b.expenses.find(x => String(x.id) === btn.dataset.del);
      if (!await confirmDialog('Delete this expense?', (ex ? money(ex.amount) + ' for ' + ex.category + (ex.description ? ' (' + ex.description + ')' : '') : 'This expense') + ' will be removed from the budget.', 'Delete expense', true)) return;
      try { update(await api('DELETE', '/api/budgets/' + encodeURIComponent(b.id) + '/expenses/' + encodeURIComponent(btn.dataset.del))); toast('Expense deleted.', 'ok'); }
      catch (err) { toast(err.message, 'bad'); }
    }));
  };
  draw();
}

function expenseDialog(b, ex, update) {
  const today = todayISO();
  const cats = b.rows.map(r => r.name);
  openDialog('<h2>' + (ex ? 'Edit expense' : 'Record expense') + '</h2><form id="xf" class="stack" novalidate><div class="formerr" role="alert"></div>' +
    fld('x-cat', 'Category', '<select id="x-cat">' + cats.map(c => '<option' + (ex && ex.category === c ? ' selected' : '') + '>' + esc(c) + '</option>').join('') + '<option value="__new">Add a new category</option></select>') +
    '<div id="x-newwrap" hidden>' + fld('x-new', 'New category name', '<input id="x-new" type="text" maxlength="60">') + '</div>' +
    '<div class="row2">' + fld('x-amt', 'Amount', '<div class="pre-wrap"><span class="pre">PKR</span><input id="x-amt" type="text" inputmode="decimal" value="' + (ex ? ex.amount : '') + '" autocomplete="off"></div>') +
    fld('x-date', 'Date', '<input id="x-date" type="date" max="' + today + '" value="' + esc(ex ? ex.date : today) + '">', 'Expenses are things already spent, so future dates are disabled.') + '</div>' +
    fld('x-desc', 'Description', '<input id="x-desc" type="text" maxlength="120" placeholder="Monthly grocery at the market" value="' + esc(ex ? ex.description : '') + '">') +
    '<div class="dfoot"><button class="btn btn-ghost" data-close type="button">Cancel</button><button class="btn btn-primary" type="submit">' + (ex ? 'Save changes' : 'Record expense') + '</button></div></form>');
  const form = $('#xf', dlg), sel = $('#x-cat', dlg);
  if (!cats.length) { sel.value = '__new'; }
  const toggle = () => { $('#x-newwrap', dlg).hidden = sel.value !== '__new'; };
  sel.addEventListener('change', toggle); toggle();
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const errs = {};
    const cat = sel.value === '__new' ? $('#x-new').value.trim() : sel.value, amt = num($('#x-amt').value), date = $('#x-date').value;
    if (!cat) errs[sel.value === '__new' ? 'x-new' : 'x-cat'] = 'Choose or enter a category.';
    if (!isFinite(amt) || amt <= 0) errs['x-amt'] = 'Enter an amount greater than zero.';
    if (!parseISO(date)) errs['x-date'] = 'Choose a date.';
    else if (date > todayISO()) errs['x-date'] = 'Choose today or an earlier date.';
    if (!fieldErrors(form, errs)) return;
    const btn = $('button[type=submit]', form);
    busy(btn, true, 'Saving');
    try {
      const body = { category: cat, amount: amt, date, description: $('#x-desc').value.trim() };
      const v = ex ? await api('PUT', '/api/budgets/' + encodeURIComponent(b.id) + '/expenses/' + encodeURIComponent(ex.id), body)
        : await api('POST', '/api/budgets/' + encodeURIComponent(b.id) + '/expenses', body);
      closeDialog(); update(v); toast(ex ? 'Expense updated.' : 'Expense recorded.', 'ok');
    } catch (err) { busy(btn, false); $('.formerr', form).textContent = err.message; }
  });
}

/* ------------------------------------------------------------------ reports */
async function pageReports(view, args, alive) {
  const files = await api('GET', '/api/reports');
  if (!alive()) return;
  view.innerHTML = '<div class="pagehead"><div><h1>PDF reports</h1><p>Every trip and budget PDF is saved in the reports folder of your project. Download any of them again here.</p></div></div>' +
    (files.length ? '<div class="tw"><table><thead><tr><th>File</th><th>Created</th><th class="num">Size</th><th><span class="sr">Download</span></th></tr></thead><tbody>' +
      files.map((f, i) => '<tr><td><span class="inline" style="gap:10px">' + icon('file', 'width="20" height="20" style="color:var(--pk);flex:none"') + '<span class="mono" style="font-size:14px;word-break:break-all">' + esc(f.name) + '</span></span></td><td class="nowrap">' + esc(new Date(f.time * 1000).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })) + '</td><td class="num">' + esc(f.kb) + ' KB</td><td><div class="acts"><button class="btn btn-ghost btn-sm" data-dl="' + i + '" type="button">' + icon('down', 'width="16" height="16"') + 'Download</button></div></td></tr>').join('') + '</tbody></table></div>'
      : '<div class="empty">' + icon('file') + '<h3>No PDF reports yet</h3><p>Confirm a trip or create a budget report and the PDF will appear here.</p><div class="inline" style="justify-content:center"><a class="btn btn-primary" href="#/plan">Plan a trip</a><a class="btn btn-ghost" href="#/budgets">Open budgets</a></div></div>');
  view.onclick = e => { const b = e.target.closest('[data-dl]'); if (b) download(files[+b.dataset.dl].name); };
}

/* ------------------------------------------------------------------ settings */
async function pageSettings(view, args, alive) {
  const dev = await api('GET', '/api/developer');
  if (!alive()) return;
  const u = state.user;
  view.innerHTML = '<div class="pagehead"><div><h1>Settings</h1><p>Your account and the developer details printed in every PDF footer.</p></div></div><div class="grid2">' +
    '<section class="panel"><h2>Developer details</h2><p class="sub">Saved to config/developer.json.</p><form id="df" class="stack" novalidate><div class="formerr" role="alert"></div>' +
    fld('d-name', 'Developer name', '<input id="d-name" type="text" value="' + esc(dev.developer_name) + '">') +
    fld('d-gh', 'GitHub username', '<div class="pre-wrap"><span class="pre">@</span><input id="d-gh" type="text" value="' + esc(dev.github_username) + '" autocomplete="off" style="font-family:var(--sans);padding-left:34px"></div>') +
    fld('d-mail', 'Email address', '<input id="d-mail" type="email" value="' + esc(dev.email) + '">') +
    '<div><button class="btn btn-primary" type="submit">Save details</button></div></form></section>' +
    '<section class="panel"><h2>Your account</h2><p class="sub">You are logged in as:</p><dl class="kv"><dt>Name</dt><dd>' + esc(u.name) + '</dd><dt>Email</dt><dd>' + esc(u.email) + '</dd></dl><div class="divider"></div><button class="btn btn-danger" id="lo2" type="button">' + icon('out', 'width="18" height="18"') + 'Log out</button></section></div>';
  const f = $('#df');
  f.addEventListener('submit', async e => {
    e.preventDefault();
    const errs = {};
    if (!$('#d-name').value.trim()) errs['d-name'] = 'Enter a developer name.';
    if (!$('#d-gh').value.trim()) errs['d-gh'] = 'Enter a GitHub username.';
    if (!EMAIL_RE.test($('#d-mail').value.trim())) errs['d-mail'] = 'Enter a valid email address.';
    if (!fieldErrors(f, errs)) return;
    const btn = $('button[type=submit]', f); busy(btn, true, 'Saving');
    try {
      await api('PUT', '/api/developer', { developer_name: $('#d-name').value.trim(), github_username: $('#d-gh').value.trim().replace(/^@/, ''), email: $('#d-mail').value.trim() });
      busy(btn, false); toast('Developer details saved. New PDFs will use them.', 'ok');
    } catch (err) { busy(btn, false); $('.formerr', f).textContent = err.message; }
  });
  $('#lo2').addEventListener('click', () => $('#logout').click());
}

/* ------------------------------------------------------------------ boot */
window.addEventListener('hashchange', render);
(async function boot() {
  try { state.user = await api('GET', '/api/me'); } catch (e) { state.user = null; }
  state.ready = true;
  render();
})();
})();
