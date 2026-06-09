/**
 * NetOps AI – Operations Dashboard
 * Read-only. Polls every 3 s. No frameworks.
 */

const STAGES = [
    { key: 'SCTASK_RECEIVED',                  label: 'SCTASK\nReceived',   icon: '📥' },
    { key: 'CHANGE_REQUEST_CREATED',            label: 'CR\nCreated',        icon: '📋' },
    { key: 'CHANGE_REQUEST_AWAITING_APPROVAL',  label: 'Awaiting\nApproval', icon: '🔐' },
    { key: 'CHANGE_REQUEST_APPROVED',           label: 'Approved',           icon: '✅' },
    { key: 'CONFIGURATION_EXECUTING',           label: 'Executing',          icon: '⚙' },
    { key: 'CONFIGURATION_VERIFIED',            label: 'Verified',           icon: '🔍' },
    { key: 'CHANGE_REQUEST_CLOSED',             label: 'CR\nClosed',         icon: '🏁' },
];

let history = [];
let booted  = false;

// ── Boot ──────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
    refresh();
    setInterval(refresh, 3000);
});

async function refresh() {
    try {
        const [metrics, active, hist, timeline] = await Promise.all([
            get('/dashboard/api/metrics'),
            get('/dashboard/api/active'),
            get('/dashboard/api/history'),
            get('/dashboard/api/timeline'),
        ]);

        renderHeader(metrics);
        renderActive(active);
        renderHistory(hist);
        renderFeed(timeline);
        renderOps(metrics);
        populateSelects(hist.history ?? []);

        const sctask = active?.active?.sctask
            ?? (hist.history?.[0]?.sctask ?? null);

        if (sctask) {
            const pipe = await get(`/dashboard/api/pipeline/${sctask}`);
            renderPipeline(pipe, sctask);
        } else {
            renderPipelineEmpty();
        }

        document.getElementById('h-refresh').textContent =
            new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        if (!booted) {
            booted = true;
            document.getElementById('boot').classList.add('hidden');
        }
    } catch (e) {
        console.error(e);
    }
}

async function get(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(r.status + ' ' + url);
    return r.json();
}

// ── Header ────────────────────────────────────────────────────────
function renderHeader(m) {
    setText('h-total',   m.total_tasks        ?? 0);
    setText('h-success', m.successful_tasks   ?? 0);
    setText('h-active',  m.in_progress_tasks  ?? 0);
    setText('h-rate',    (m.success_rate ?? 0) + '%');
}

// ── Active task ───────────────────────────────────────────────────
function renderActive(data) {
    const task  = data?.active;
    const body  = el('active-body');
    const chip  = el('active-chip');

    if (!task) {
        chip.textContent = 'IDLE';
        chip.className   = 'status-chip idle';
        body.innerHTML   = '<div class="empty">No active tasks</div>';
        return;
    }

    chip.textContent = task.stage?.toUpperCase() ?? 'ACTIVE';
    chip.className   = 'status-chip active';

    body.innerHTML = `
    <div class="active-task">
        <div class="active-row">
            <div>
                <div class="active-field-label">SCTASK</div>
                <div class="active-field-val cyan">${x(task.sctask)}</div>
            </div>
            <div>
                <div class="active-field-label">Change Request</div>
                <div class="active-field-val">${x(task.cr ?? '—')}</div>
            </div>
            <div>
                <div class="active-field-label">Device</div>
                <div class="active-field-val">${x(task.device ?? '—')}</div>
            </div>
            <div>
                <div class="active-field-label">Updated</div>
                <div class="active-field-val amber">${ago(task.last_update)}</div>
            </div>
        </div>
        <div class="active-desc">${x(task.short_description ?? '')}</div>
    </div>`;
}

// ── Pipeline ──────────────────────────────────────────────────────
function renderPipeline(data, label) {
    el('pipeline-label').textContent = label ?? '';

    const map  = data?.pipeline_stages ?? {};
    const done = STAGES.filter(s => map[s.key]?.completed).length;
    const pct  = Math.round(done / STAGES.length * 100);

    el('pipe-fill').style.width = pct + '%';

    el('pipeline-steps').innerHTML = STAGES.map((s, i) => {
        const info   = map[s.key] ?? {};
        const isDone = !!info.completed;
        const prevDone = i === 0 || STAGES.slice(0, i).some(p => map[p.key]?.completed);
        const isActive = !isDone && prevDone && done < STAGES.length;
        const isFailed = info.status === 'failed';

        const cls = isFailed ? 'failed' : isDone ? 'done' : isActive ? 'active' : '';
        const ts  = info.timestamp
            ? `<div class="pipe-time">${fmt(info.timestamp)}</div>`
            : '';

        return `<div class="pipe-step ${cls}">
            <div class="pipe-node">${s.icon}</div>
            <div class="pipe-label">${s.label.replace('\n', '<br>')}</div>
            ${ts}
        </div>`;
    }).join('');
}

function renderPipelineEmpty() {
    el('pipeline-label').textContent = '';
    el('pipe-fill').style.width = '0%';
    el('pipeline-steps').innerHTML = STAGES.map(s =>
        `<div class="pipe-step">
            <div class="pipe-node">${s.icon}</div>
            <div class="pipe-label">${s.label.replace('\n', '<br>')}</div>
        </div>`
    ).join('');
}

// ── History ───────────────────────────────────────────────────────
function renderHistory(data) {
    history = data?.history ?? [];
    el('hist-count').textContent = history.length;
    const body = el('hist-body');

    if (!history.length) {
        body.innerHTML = '<div class="empty">No history</div>';
        return;
    }

    body.innerHTML = history.map(t => {
        const stage = (t.lifecycle_stage ?? '').toLowerCase();
        const cls   = stage === 'closed' ? 'closed' : t.status === 'failed' ? 'failed' : 'open';
        return `<div class="hist-item" onclick="pick('${x(t.sctask)}')">
            <div class="hist-top">
                <span class="hist-id">${x(t.sctask)}</span>
                <span class="badge ${cls}">${x(t.lifecycle_stage ?? '—')}</span>
            </div>
            <div class="hist-desc">${x(t.short_description ?? '')}</div>
            <div class="hist-meta">${x(t.cr ?? '—')} · ${x(t.device ?? '—')} · ${dur(t.started_at, t.completed_at)}</div>
        </div>`;
    }).join('');
}

// ── Feed ──────────────────────────────────────────────────────────
function renderFeed(data) {
    const events = (data?.events ?? []).slice(0, 25);
    el('feed-count').textContent = (data?.count ?? 0) + ' events';
    const body = el('feed-body');

    if (!events.length) {
        body.innerHTML = '<div class="empty">No events</div>';
        return;
    }

    body.innerHTML = events.map(e => `
        <div class="feed-item">
            <div class="feed-indicator ${e.severity ?? 'info'}"></div>
            <div class="feed-content">
                <div class="feed-stage ${e.severity ?? 'info'}">${x(e.stage ?? '')}</div>
                <div class="feed-msg">${x(e.message ?? '')}</div>
                <div class="feed-meta">${x(e.sctask ?? '—')} · ${x(e.device ?? '—')}</div>
            </div>
            <div class="feed-time">${ago(e.timestamp)}</div>
        </div>`
    ).join('');
}

// ── Ops breakdown ─────────────────────────────────────────────────
function renderOps(m) {
    const ops  = m.operation_breakdown ?? {};
    const body = el('ops-body');
    const list = Object.entries(ops).sort((a, b) => b[1] - a[1]);
    const max  = list[0]?.[1] ?? 1;

    if (!list.length) { body.innerHTML = '<div class="empty">No data</div>'; return; }

    body.innerHTML = list.map(([name, count]) => `
        <div class="ops-item">
            <div class="ops-name">${x(name.replace(/_/g, ' '))}</div>
            <div class="ops-bar-bg"><div class="ops-bar-fill" style="width:${Math.round(count/max*100)}%"></div></div>
            <div class="ops-count">${count}</div>
        </div>`
    ).join('');
}

// ── Selects ───────────────────────────────────────────────────────
function populateSelects(hist) {
    ['diff-selector', 'detail-selector'].forEach(id => {
        const s   = el(id);
        const cur = s.value;
        s.innerHTML = '<option value="">Select task…</option>' +
            hist.map(t =>
                `<option value="${x(t.sctask)}">${x(t.sctask)} — ${x((t.short_description ?? '').substring(0, 40))}</option>`
            ).join('');
        if (cur) s.value = cur;
    });
}

function pick(sctask) {
    ['diff-selector', 'detail-selector'].forEach(id => { el(id).value = sctask; });
    loadDiff();
    loadDetails();
}

// ── Diff ──────────────────────────────────────────────────────────
async function loadDiff() {
    const sctask = el('diff-selector').value;
    const body   = el('diff-body');

    if (!sctask) {
        body.innerHTML = `<div class="diff-empty">
            <div class="diff-empty-icon">&#8644;</div>
            <div class="diff-empty-text">Select a task to compare device state before and after the configuration push.</div>
        </div>`;
        return;
    }

    body.innerHTML = '<div class="empty">Loading…</div>';

    try {
        const d = await get(`/dashboard/api/history/${sctask}`);
        renderDiff(body, d);
    } catch (e) {
        body.innerHTML = `<div class="empty">Error: ${e.message}</div>`;
    }
}

function renderDiff(container, d) {
    const before = d.before_state ?? {};
    const after  = d.after_state  ?? {};
    const plan   = d.execution_plan ?? [];
    const device = d.device_data ?? {};

    const noState = !Object.keys(before).length && !Object.keys(after).length;
    if (noState) {
        container.innerHTML = `<div class="diff-empty">
            <div class="diff-empty-icon">⏳</div>
            <div class="diff-empty-text">State snapshots are captured from the next run onwards. Tasks completed before this feature was enabled do not have device state data.</div>
        </div>`;
        return;
    }

    const bVlans = vlans(before);
    const aVlans = vlans(after);
    const bIfaces = ifaces(before);
    const aIfaces = ifaces(after);

    const addedIds   = plan.filter(s => s.intent_type === 'create_vlan').map(s => Number(s.parameters?.vlan_id));
    const removedIds = plan.filter(s => s.intent_type === 'delete_vlan').map(s => Number(s.parameters?.vlan_id));
    const changedIf  = plan
        .filter(s => ['configure_access_port','configure_trunk_port','configure_interface_status'].includes(s.intent_type))
        .map(s => s.parameters?.interface);

    container.innerHTML = `
    <div class="diff-grid">
        <div class="diff-pane before">
            <div class="diff-pane-head">⚠ BEFORE</div>
            <div class="diff-pane-body">
                ${deviceInfoBlock(device, before)}
                ${vlanBlock(bVlans, addedIds, removedIds, 'before')}
                ${bIfaces.length ? ifaceBlock(bIfaces, changedIf, 'before') : ''}
            </div>
        </div>
        <div class="diff-pane after">
            <div class="diff-pane-head">✔ AFTER</div>
            <div class="diff-pane-body">
                ${deviceInfoBlock(device, after)}
                ${vlanBlock(aVlans, addedIds, removedIds, 'after')}
                ${aIfaces.length ? ifaceBlock(aIfaces, changedIf, 'after') : ''}
            </div>
        </div>
    </div>`;
}

function deviceInfoBlock(dev, snap) {
    const info = snap?.device_info ?? {};
    const rows = [
        dev.device_name  ? `<div class="diff-kv"><span class="dk">Name</span><span class="dv">${x(dev.device_name)}</span></div>` : '',
        dev.model        ? `<div class="diff-kv"><span class="dk">Model</span><span class="dv">${x(dev.model)}</span></div>` : '',
        dev.os_type      ? `<div class="diff-kv"><span class="dk">OS</span><span class="dv">${x(dev.os_type)}</span></div>` : '',
        info.os_version  ? `<div class="diff-kv"><span class="dk">Version</span><span class="dv">${x(info.os_version)}</span></div>` : '',
    ].filter(Boolean).join('');
    return rows ? `<div class="diff-section">Device</div>${rows}` : '';
}

function vlanBlock(list, addedIds, removedIds, side) {
    if (!list.length) return `<div class="diff-section">VLANs</div><div style="font-size:11px;color:var(--text3);padding:4px 0">No VLAN data</div>`;

    const rows = list.map(v => {
        const id  = Number(v.vlan_id ?? v.id ?? 0);
        let cls = '', tag = '';
        if (side === 'before' && removedIds.includes(id)) { cls = 'row-removed'; tag = `<span class="mini-tag removed">REMOVE</span>`; }
        if (side === 'after'  && addedIds.includes(id))   { cls = 'row-added';   tag = `<span class="mini-tag added">NEW</span>`; }
        return `<tr class="${cls}">
            <td>${id}${tag}</td>
            <td>${x(v.name ?? v.vlan_name ?? '—')}</td>
            <td>${x(v.status ?? v.state ?? '—')}</td>
        </tr>`;
    });

    return `<div class="diff-section">VLANs (${list.length})</div>
    <table class="diff-table">
        <tr><th>ID</th><th>Name</th><th>Status</th></tr>
        ${rows.join('')}
    </table>`;
}

function ifaceBlock(list, changedIf, side) {
    const rows = list.slice(0, 8).map(i => {
        const name = i.name ?? '';
        const cls  = changedIf?.includes(name) ? (side === 'after' ? 'row-added' : 'row-removed') : '';
        const tag  = changedIf?.includes(name) ? `<span class="mini-tag changed">CHG</span>` : '';
        return `<tr class="${cls}">
            <td>${x(name)}${tag}</td>
            <td>${x(i.mode ?? '—')}</td>
            <td>${x(i.access_vlan ?? i.vlan ?? '—')}</td>
        </tr>`;
    });

    return `<div class="diff-section" style="margin-top:8px">Interfaces</div>
    <table class="diff-table">
        <tr><th>Name</th><th>Mode</th><th>VLAN</th></tr>
        ${rows.join('')}
    </table>`;
}

// ── Details ───────────────────────────────────────────────────────
async function loadDetails() {
    const sctask = el('detail-selector').value;
    const body   = el('detail-body');

    if (!sctask) { body.innerHTML = '<div class="empty">Select a task</div>'; return; }
    body.innerHTML = '<div class="empty">Loading…</div>';

    try {
        const d = await get(`/dashboard/api/history/${sctask}`);
        renderDetails(body, d);
    } catch (e) {
        body.innerHTML = `<div class="empty">Error: ${e.message}</div>`;
    }
}

function renderDetails(container, d) {
    const dev   = d.device_data ?? {};
    const steps = d.execution_plan ?? [];
    const hist  = d.stage_history ?? [];

    let html = `
    <div class="det-section">
        <div class="det-label">Task Info</div>
        <div class="det-kv"><span class="det-k">SCTASK</span><span class="det-v cyan">${x(d.sctask)}</span></div>
        <div class="det-kv"><span class="det-k">CR</span><span class="det-v">${x(d.cr ?? '—')}</span></div>
        <div class="det-kv"><span class="det-k">Stage</span><span class="det-v">${x(d.lifecycle_stage ?? '—')}</span></div>
    </div>
    <div class="det-section">
        <div class="det-label">Device</div>
        <div class="det-kv"><span class="det-k">Name</span><span class="det-v">${x(dev.device_name ?? '—')}</span></div>
        <div class="det-kv"><span class="det-k">Model</span><span class="det-v">${x(dev.model ?? '—')}</span></div>
        <div class="det-kv"><span class="det-k">OS</span><span class="det-v">${x(dev.os_type ?? '—')}</span></div>
        <div class="det-kv"><span class="det-k">Host</span><span class="det-v">${x(dev.management_host ?? '—')}</span></div>
    </div>`;

    if (steps.length) {
        html += `<div class="det-section"><div class="det-label">Steps</div>`;
        html += steps.map(s => `
            <div class="step-card ${s.execute ? 'success' : ''}">
                <div class="step-top">
                    <span class="step-name">Step ${s.step} — ${x((s.intent_type ?? '').replace(/_/g, ' '))}</span>
                    <span class="step-badge ${s.execute ? 'success' : 'pending'}">${s.execute ? 'Run' : 'Skip'}</span>
                </div>
                <div class="step-params">${x(JSON.stringify(s.parameters ?? {}).replace(/[{}"]/g, ''))}</div>
            </div>`).join('');
        html += `</div>`;
    }

    if (hist.length) {
        html += `<div class="det-section"><div class="det-label">History</div>`;
        html += hist.map(e => `
            <div class="det-kv">
                <span class="det-k">${fmt(e.timestamp)}</span>
                <span class="det-v ${e.status === 'success' ? 'green' : e.status === 'failed' ? 'red' : ''}">${x(e.stage ?? '')}</span>
            </div>`).join('');
        html += `</div>`;
    }

    container.innerHTML = html;
}

// ── Utilities ─────────────────────────────────────────────────────
function vlans(state) {
    if (!state || typeof state !== 'object') return [];
    const raw = state._raw_vlans ?? state.vlans ?? [];
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'object') return Object.values(raw);
    return [];
}

function ifaces(state) {
    if (!state || typeof state !== 'object') return [];
    const raw = state.interfaces ?? [];
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'object') return Object.values(raw);
    return [];
}

function ago(iso) {
    if (!iso) return '—';
    const s = Math.floor((Date.now() - new Date(iso)) / 1000);
    if (s < 60)    return s + 's ago';
    if (s < 3600)  return Math.floor(s / 60) + 'm ago';
    if (s < 86400) return Math.floor(s / 3600) + 'h ago';
    return Math.floor(s / 86400) + 'd ago';
}

function fmt(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function dur(start, end) {
    if (!start || !end) return '—';
    const s = Math.floor((new Date(end) - new Date(start)) / 1000);
    return s < 60 ? s + 's' : Math.floor(s / 60) + 'm ' + (s % 60) + 's';
}

function x(str) {
    return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function el(id)       { return document.getElementById(id); }
function setText(id, v) { const e = el(id); if (e) e.textContent = v; }
