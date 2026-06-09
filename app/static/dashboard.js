/**
 * NetOps AI – Operations Dashboard
 * Read-only. All data from existing backend.
 * Refresh: every 3 s via polling.
 */

// ── Pipeline stage definitions ─────────────────────────────────────────────
const PIPELINE_STAGES = [
    { key: 'SCTASK_RECEIVED',              label: 'SCTASK\nReceived',     icon: '📥' },
    { key: 'CHANGE_REQUEST_CREATED',       label: 'CR\nCreated',          icon: '📋' },
    { key: 'CHANGE_REQUEST_AWAITING_APPROVAL', label: 'Awaiting\nApproval', icon: '🔐' },
    { key: 'CHANGE_REQUEST_APPROVED',      label: 'Approved',             icon: '✅' },
    { key: 'CONFIGURATION_EXECUTING',      label: 'Executing\nConfig',    icon: '⚙️' },
    { key: 'CONFIGURATION_VERIFIED',       label: 'Verified',             icon: '🔍' },
    { key: 'CHANGE_REQUEST_CLOSED',        label: 'CR\nClosed',           icon: '🏁' },
];

// ── State ──────────────────────────────────────────────────────────────────
let allHistory = [];
let currentActiveSctask = null;

// ── Boot ──────────────────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
    await refreshAll();
    setInterval(refreshAll, 3000);
});

async function refreshAll() {
    try {
        const [metricsData, activeData, historyData, timelineData] = await Promise.all([
            apiFetch('/dashboard/api/metrics'),
            apiFetch('/dashboard/api/active'),
            apiFetch('/dashboard/api/history'),
            apiFetch('/dashboard/api/timeline'),
        ]);

        renderHeader(metricsData);
        renderActiveTask(activeData);
        renderHistory(historyData);
        renderFeed(timelineData);
        renderOpsBreakdown(metricsData);

        // If there's an active task, load its pipeline
        const activeSctask = activeData?.active?.sctask;
        if (activeSctask && activeSctask !== currentActiveSctask) {
            currentActiveSctask = activeSctask;
        }
        if (activeSctask) {
            const pipeline = await apiFetch(`/dashboard/api/pipeline/${activeSctask}`);
            renderPipeline(pipeline, activeSctask);
        } else if (allHistory.length > 0) {
            // Show pipeline for the most recent completed task
            const latest = allHistory[0];
            if (latest?.sctask) {
                const pipeline = await apiFetch(`/dashboard/api/pipeline/${latest.sctask}`);
                renderPipeline(pipeline, latest.sctask + ' (completed)');
            }
        } else {
            renderEmptyPipeline();
        }

        hideBoot();
        document.getElementById('h-refresh').textContent = new Date().toLocaleTimeString();

    } catch (err) {
        console.error('Dashboard refresh error:', err);
    }
}

// ── API helper ────────────────────────────────────────────────────────────
async function apiFetch(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${r.status} ${url}`);
    return r.json();
}

// ── Header stats ─────────────────────────────────────────────────────────
function renderHeader(m) {
    document.getElementById('h-total').textContent   = m.total_tasks   ?? 0;
    document.getElementById('h-success').textContent = m.successful_tasks ?? 0;
    document.getElementById('h-active').textContent  = m.in_progress_tasks ?? 0;
    document.getElementById('h-rate').textContent    = (m.success_rate ?? 0) + '%';
}

// ── Active task ───────────────────────────────────────────────────────────
function renderActiveTask(data) {
    const el    = document.getElementById('active-body');
    const badge = document.getElementById('active-badge');
    const task  = data?.active;

    if (!task) {
        badge.textContent = 'IDLE';
        badge.className   = 'card-badge';
        el.innerHTML      = '<div class="empty-state">No active tasks</div>';
        return;
    }

    badge.textContent = task.stage?.toUpperCase() ?? 'ACTIVE';
    badge.className   = 'card-badge pulse active';

    el.innerHTML = `
        <div class="active-task-grid">
            <div>
                <div class="atg-key">SCTASK</div>
                <div class="atg-val accent">${esc(task.sctask)}</div>
            </div>
            <div>
                <div class="atg-key">Change Request</div>
                <div class="atg-val">${esc(task.cr ?? '—')}</div>
            </div>
            <div>
                <div class="atg-key">Device</div>
                <div class="atg-val">${esc(task.device ?? '—')}</div>
            </div>
            <div>
                <div class="atg-key">Stage</div>
                <div class="atg-val amber">${esc(task.stage ?? '—')}</div>
            </div>
            <div class="atg-full">
                <div class="atg-key">Last Updated</div>
                <div class="atg-val">${timeAgo(task.last_update)}</div>
            </div>
        </div>
        <div class="atg-desc">${esc(task.short_description ?? '')}</div>
    `;
}

// ── Pipeline ──────────────────────────────────────────────────────────────
function renderPipeline(data, labelText) {
    document.getElementById('pipeline-task-label').textContent = labelText ?? '—';

    const stageMap  = data?.pipeline_stages ?? {};
    const container = document.getElementById('pipeline-track');

    // Count completed steps for progress bar
    const done = PIPELINE_STAGES.filter(s => stageMap[s.key]?.completed).length;
    const pct  = Math.round((done / PIPELINE_STAGES.length) * 100);

    let html = '';
    PIPELINE_STAGES.forEach((s, i) => {
        const info   = stageMap[s.key] ?? {};
        const isDone = !!info.completed;

        // Determine if this is the "active" step (first non-completed after a completed one)
        const prevDone = i === 0 || PIPELINE_STAGES.slice(0, i).some(p => stageMap[p.key]?.completed);
        const isActive = !isDone && prevDone && done < PIPELINE_STAGES.length;
        const isFailed = info.status === 'failed';

        const cls = isFailed ? 'failed' : isDone ? 'done' : isActive ? 'active' : '';
        const ts  = info.timestamp ? `<div class="pipe-time">${fmtTime(info.timestamp)}</div>` : '';

        html += `
        <div class="pipe-step ${cls}">
            <div class="pipe-circle">${s.icon}</div>
            <div class="pipe-label">${s.label.replace('\n', '<br>')}</div>
            ${ts}
        </div>`;
    });

    container.innerHTML = html;

    // Inject/update progress bar
    let bar = document.getElementById('pipeline-bar-wrap');
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'pipeline-bar-wrap';
        bar.className = 'pipeline-progress';
        bar.innerHTML = '<div class="pipeline-progress-fill" id="pipeline-bar-fill"></div>';
        container.parentElement.insertBefore(bar, container);
    }
    document.getElementById('pipeline-bar-fill').style.width = pct + '%';
}

function renderEmptyPipeline() {
    document.getElementById('pipeline-task-label').textContent = '—';
    let html = '';
    PIPELINE_STAGES.forEach(s => {
        html += `<div class="pipe-step"><div class="pipe-circle">${s.icon}</div><div class="pipe-label">${s.label.replace('\n', '<br>')}</div></div>`;
    });
    document.getElementById('pipeline-track').innerHTML = html;
}

// ── History list ──────────────────────────────────────────────────────────
function renderHistory(data) {
    allHistory = data?.history ?? [];
    const el   = document.getElementById('hist-body');

    document.getElementById('hist-count').textContent = allHistory.length;
    populateSelectors(allHistory);

    if (!allHistory.length) {
        el.innerHTML = '<div class="empty-state">No history yet</div>';
        return;
    }

    el.innerHTML = allHistory.map(t => {
        const stage  = (t.lifecycle_stage ?? '').toLowerCase();
        const cls    = stage === 'closed' ? 'closed' : t.status === 'success' ? 'closed' : 'open';
        const label  = t.lifecycle_stage ?? 'Unknown';
        const dur    = calcDuration(t.started_at, t.completed_at);

        return `
        <div class="hist-item" onclick="selectTask('${esc(t.sctask)}')">
            <div class="hist-row1">
                <span class="hist-id">${esc(t.sctask)}</span>
                <span class="hist-badge ${cls}">${esc(label)}</span>
            </div>
            <div class="hist-desc">${esc(t.short_description ?? '')}</div>
            <div class="hist-meta">📋 ${esc(t.cr ?? '—')} &nbsp;·&nbsp; 🔧 ${esc(t.device ?? '—')} &nbsp;·&nbsp; ⏱ ${dur}</div>
        </div>`;
    }).join('');
}

// ── Activity feed ─────────────────────────────────────────────────────────
function renderFeed(data) {
    const events = (data?.events ?? []).slice(0, 30);
    const el     = document.getElementById('feed-body');

    document.getElementById('feed-count').textContent = (data?.count ?? 0) + ' events';

    if (!events.length) {
        el.innerHTML = '<div class="empty-state">No events yet</div>';
        return;
    }

    el.innerHTML = events.map(e => `
        <div class="feed-item">
            <div class="feed-dot ${e.severity ?? 'info'}"></div>
            <div class="feed-content">
                <div class="feed-stage ${e.severity ?? 'info'}">${esc(e.stage ?? '')}</div>
                <div class="feed-msg">${esc(e.message ?? '')}</div>
                <div class="feed-meta">${esc(e.sctask ?? '—')} &nbsp;·&nbsp; ${esc(e.device ?? '—')}</div>
            </div>
            <div class="feed-time">${timeAgo(e.timestamp)}</div>
        </div>
    `).join('');
}

// ── Ops breakdown ─────────────────────────────────────────────────────────
function renderOpsBreakdown(m) {
    const ops = m.operation_breakdown ?? {};
    const el  = document.getElementById('ops-body');

    const entries = Object.entries(ops).sort((a, b) => b[1] - a[1]);
    const max     = entries[0]?.[1] ?? 1;

    if (!entries.length) {
        el.innerHTML = '<div class="empty-state">No operations yet</div>';
        return;
    }

    el.innerHTML = entries.map(([name, count]) => `
        <div class="ops-row">
            <div class="ops-name">${esc(name.replace(/_/g, ' '))}</div>
            <div class="ops-count-wrap">
                <div class="ops-bar-bg"><div class="ops-bar-fill" style="width:${Math.round(count/max*100)}%"></div></div>
                <div class="ops-num">${count}</div>
            </div>
        </div>
    `).join('');
}

// ── Selectors (diff + details) ────────────────────────────────────────────
function populateSelectors(history) {
    ['diff-selector', 'detail-selector'].forEach(id => {
        const sel = document.getElementById(id);
        const cur = sel.value;
        sel.innerHTML = '<option value="">Select task…</option>' +
            history.map(t => `<option value="${esc(t.sctask)}">${esc(t.sctask)} — ${esc((t.short_description ?? '').substring(0, 45))}</option>`).join('');
        if (cur) sel.value = cur;
    });
}

// ── Select from history sidebar ───────────────────────────────────────────
function selectTask(sctask) {
    ['diff-selector', 'detail-selector'].forEach(id => {
        document.getElementById(id).value = sctask;
    });
    loadDiff();
    loadDetails();
}

// ── Before / After Diff ───────────────────────────────────────────────────
async function loadDiff() {
    const sctask = document.getElementById('diff-selector').value;
    const body   = document.getElementById('diff-body');

    if (!sctask) {
        body.innerHTML = diffPlaceholder();
        return;
    }

    body.innerHTML = '<div class="empty-state">Loading…</div>';

    try {
        const data = await apiFetch(`/dashboard/api/history/${sctask}`);
        renderDiff(body, data);
    } catch (e) {
        body.innerHTML = `<div class="empty-state">Failed to load: ${e.message}</div>`;
    }
}

function diffPlaceholder() {
    return `<div class="diff-placeholder">
        <div class="diff-placeholder-icon">⇄</div>
        <div class="diff-placeholder-text">Select a task above to view the device state before &amp; after the configuration push.</div>
    </div>`;
}

function renderDiff(container, data) {
    const before = data.before_state ?? {};
    const after  = data.after_state  ?? {};
    const plan   = data.execution_plan ?? [];
    const device = data.device_data   ?? {};

    const noData = !Object.keys(before).length && !Object.keys(after).length;
    if (noData) {
        container.innerHTML = `
        <div class="diff-placeholder">
            <div class="diff-placeholder-icon">⏳</div>
            <div class="diff-placeholder-text">
                Before/After state data will be captured from the next automation run.<br>
                Older tasks completed before this feature was enabled do not have persisted device snapshots.
            </div>
        </div>`;
        return;
    }

    // Extract VLAN lists
    const beforeVlans = extractVlans(before);
    const afterVlans  = extractVlans(after);
    const beforeInterfaces = extractInterfaces(before);
    const afterInterfaces  = extractInterfaces(after);

    // Compute what changed based on execution plan
    const addedVlans   = plan.filter(s => s.intent_type === 'create_vlan').map(s => s.parameters?.vlan_id);
    const removedVlans = plan.filter(s => s.intent_type === 'delete_vlan').map(s => s.parameters?.vlan_id);
    const changedPorts = plan.filter(s => ['configure_access_port', 'configure_trunk_port', 'configure_interface_status'].includes(s.intent_type))
                             .map(s => s.parameters?.interface);

    // Summary stats
    const summary = buildSummary(before, after, plan);

    container.innerHTML = `
    <!-- Summary row -->
    <div class="diff-stat-row">
        ${summary.map(s => `<div class="diff-stat"><span class="ds-key">${esc(s.key)}:</span><span class="ds-val">${esc(s.val)}</span></div>`).join('')}
    </div>

    <div class="diff-grid" style="margin-top:0.75rem;">
        <!-- BEFORE -->
        <div class="diff-pane before">
            <div class="diff-pane-header">⚠ BEFORE — Pre-change Snapshot</div>
            <div class="diff-pane-body">
                ${renderVlanTable(beforeVlans, addedVlans, removedVlans, 'before')}
                ${beforeInterfaces.length ? renderInterfaceTable(beforeInterfaces, changedPorts, 'before') : ''}
                ${renderDeviceInfo(device, before)}
            </div>
        </div>

        <!-- AFTER -->
        <div class="diff-pane after">
            <div class="diff-pane-header">✅ AFTER — Post-change Verified State</div>
            <div class="diff-pane-body">
                ${renderVlanTable(afterVlans, addedVlans, removedVlans, 'after')}
                ${afterInterfaces.length ? renderInterfaceTable(afterInterfaces, changedPorts, 'after') : ''}
                ${renderDeviceInfo(device, after)}
            </div>
        </div>
    </div>`;
}

function buildSummary(before, after, plan) {
    const bv = extractVlans(before).length;
    const av = extractVlans(after).length;
    const diff = av - bv;
    const ops  = [...new Set(plan.map(s => s.intent_type))].join(', ');

    const rows = [];
    rows.push({ key: 'Device', val: before.device_info?.hostname ?? after.device_info?.hostname ?? '—' });
    rows.push({ key: 'OS', val: before.device_info?.os_version ?? after.device_info?.os_version ?? '—' });
    if (bv || av) rows.push({ key: 'VLANs Before/After', val: `${bv} → ${av}  (${diff >= 0 ? '+' : ''}${diff})` });
    if (ops) rows.push({ key: 'Operations', val: ops.replace(/_/g, ' ') });
    rows.push({ key: 'Steps', val: plan.length });
    return rows;
}

function renderDeviceInfo(deviceData, stateSnap) {
    const info = stateSnap?.device_info ?? {};
    if (!Object.keys(info).length && !Object.keys(deviceData).length) return '';
    return `
    <div class="diff-section-label">Device Info</div>
    <table class="diff-table">
        <tr><th>Field</th><th>Value</th></tr>
        ${deviceData.device_name ? `<tr><td>Name</td><td>${esc(deviceData.device_name)}</td></tr>` : ''}
        ${deviceData.model       ? `<tr><td>Model</td><td>${esc(deviceData.model)}</td></tr>` : ''}
        ${deviceData.os_type     ? `<tr><td>OS Type</td><td>${esc(deviceData.os_type)}</td></tr>` : ''}
        ${info.os_version        ? `<tr><td>OS Version</td><td>${esc(info.os_version)}</td></tr>` : ''}
        ${deviceData.management_host ? `<tr><td>Host</td><td>${esc(deviceData.management_host)}</td></tr>` : ''}
    </table>`;
}

function renderVlanTable(vlans, addedIds, removedIds, side) {
    if (!vlans.length) return `<div class="diff-section-label">VLANs</div><div style="font-size:0.75rem;color:var(--text-muted);padding:0.3rem 0;">No VLAN data captured</div>`;

    const rows = vlans.map(v => {
        const id = Number(v.vlan_id ?? v.id ?? 0);
        let cls = '', tag = '';
        if (side === 'before' && removedIds.includes(id)) { cls = 'row-removed'; tag = '<span class="diff-tag removed">REMOVED</span>'; }
        if (side === 'after'  && addedIds.includes(id))   { cls = 'row-added';   tag = '<span class="diff-tag added">ADDED</span>'; }
        if (side === 'before' && addedIds.includes(id))   { cls = 'row-removed'; tag = '<span class="diff-tag removed">PENDING ADD</span>'; }
        const name = v.name ?? v.vlan_name ?? '—';
        return `<tr class="${cls}"><td>${id}${tag}</td><td>${esc(name)}</td><td>${esc(v.status ?? v.state ?? '—')}</td></tr>`;
    });

    return `
    <div class="diff-section-label">VLANs (${vlans.length})</div>
    <table class="diff-table">
        <tr><th>ID</th><th>Name</th><th>Status</th></tr>
        ${rows.join('')}
    </table>`;
}

function renderInterfaceTable(ifaces, changedPorts, side) {
    if (!ifaces.length) return '';
    const rows = ifaces.slice(0, 10).map(iface => {
        const name = iface.name ?? '';
        const isChanged = changedPorts?.includes(name);
        const cls = isChanged ? (side === 'after' ? 'row-added' : 'row-removed') : '';
        const tag = isChanged ? `<span class="diff-tag changed">CHANGED</span>` : '';
        return `<tr class="${cls}">
            <td>${esc(name)}${tag}</td>
            <td>${esc(iface.mode ?? '—')}</td>
            <td>${esc(iface.access_vlan ?? iface.vlan ?? '—')}</td>
            <td>${esc(iface.status ?? '—')}</td>
        </tr>`;
    });

    return `
    <div class="diff-section-label" style="margin-top:0.75rem;">Interfaces (showing 10)</div>
    <table class="diff-table">
        <tr><th>Name</th><th>Mode</th><th>VLAN</th><th>Status</th></tr>
        ${rows.join('')}
    </table>`;
}

// ── Execution details ─────────────────────────────────────────────────────
async function loadDetails() {
    const sctask = document.getElementById('detail-selector').value;
    const body   = document.getElementById('detail-body');

    if (!sctask) {
        body.innerHTML = '<div class="empty-state">Select a task to inspect</div>';
        return;
    }

    body.innerHTML = '<div class="empty-state">Loading…</div>';

    try {
        const data = await apiFetch(`/dashboard/api/history/${sctask}`);
        renderDetails(body, data);
    } catch (e) {
        body.innerHTML = `<div class="empty-state">Failed: ${e.message}</div>`;
    }
}

function renderDetails(el, d) {
    const device = d.device_data ?? {};
    const steps  = d.execution_plan ?? [];
    const history= d.stage_history ?? [];

    let html = `
    <div class="detail-section">
        <div class="detail-label">Task Info</div>
        <div class="detail-kv"><span class="dk">SCTASK</span><span class="dv accent">${esc(d.sctask)}</span></div>
        <div class="detail-kv"><span class="dk">CR</span><span class="dv">${esc(d.cr ?? '—')}</span></div>
        <div class="detail-kv"><span class="dk">Stage</span><span class="dv">${esc(d.lifecycle_stage ?? '—')}</span></div>
    </div>
    <div class="detail-section">
        <div class="detail-label">Device</div>
        <div class="detail-kv"><span class="dk">Name</span><span class="dv">${esc(device.device_name ?? '—')}</span></div>
        <div class="detail-kv"><span class="dk">Model</span><span class="dv">${esc(device.model ?? '—')}</span></div>
        <div class="detail-kv"><span class="dk">OS</span><span class="dv">${esc(device.os_type ?? '—')}</span></div>
        <div class="detail-kv"><span class="dk">Host</span><span class="dv">${esc(device.management_host ?? '—')}</span></div>
    </div>`;

    if (steps.length) {
        html += '<div class="detail-section"><div class="detail-label">Execution Steps</div>';
        html += steps.map(s => {
            const params = JSON.stringify(s.parameters ?? {}, null, 1)
                .replace(/\n/g, ' ').replace(/\s+/g, ' ');
            return `<div class="step-block">
                <div class="step-head">
                    <span class="step-op">Step ${s.step} — ${esc((s.intent_type ?? '').replace(/_/g, ' '))}</span>
                    <span class="step-badge ${s.execute ? 'success' : 'pending'}">${s.execute ? 'Execute' : 'Skip'}</span>
                </div>
                <div class="step-params">${esc(params)}</div>
            </div>`;
        }).join('');
        html += '</div>';
    }

    if (history.length) {
        html += '<div class="detail-section"><div class="detail-label">Stage History</div>';
        html += history.map(e => `
            <div class="detail-kv">
                <span class="dk">${fmtTime(e.timestamp)}</span>
                <span class="dv ${e.status === 'success' ? 'green' : e.status === 'failed' ? 'red' : ''}">${esc(e.stage ?? '')}</span>
            </div>`).join('');
        html += '</div>';
    }

    el.innerHTML = html;
}

// ── Helpers ───────────────────────────────────────────────────────────────
function extractVlans(state) {
    if (!state || typeof state !== 'object') return [];
    const raw = state._raw_vlans ?? state.vlans ?? [];
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'object') return Object.values(raw);
    return [];
}

function extractInterfaces(state) {
    if (!state || typeof state !== 'object') return [];
    const raw = state.interfaces ?? [];
    if (Array.isArray(raw)) return raw;
    if (typeof raw === 'object') return Object.values(raw);
    return [];
}

function timeAgo(iso) {
    if (!iso) return '—';
    const diff = Date.now() - new Date(iso).getTime();
    const s = Math.floor(diff / 1000);
    if (s < 60)   return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s/60)}m ago`;
    if (s < 86400)return `${Math.floor(s/3600)}h ago`;
    return `${Math.floor(s/86400)}d ago`;
}

function fmtTime(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function calcDuration(start, end) {
    if (!start || !end) return '—';
    const ms = new Date(end) - new Date(start);
    const s  = Math.floor(ms / 1000);
    return s < 60 ? `${s}s` : `${Math.floor(s/60)}m ${s%60}s`;
}

function esc(str) {
    return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function hideBoot() {
    const el = document.getElementById('boot-loader');
    if (el && !el.classList.contains('hidden')) el.classList.add('hidden');
}