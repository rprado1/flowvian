// ============================================================
// Workflow EXE Builder — Main App
// ============================================================

// Node registry (populated after scripts load)
const NODE_DEFS = {
  scheduler:            SchedulerNode,
  set_variables:        SetVariablesNode,
  get_current_date_utc: GetCurrentDateUTCNode,
};

// ============================================================
// State
// ============================================================
let editor          = null;   // Drawflow instance
let currentWfId     = null;   // active workflow id
let currentWfName   = '';
let selectedNodeId  = null;   // drawflow internal node id
let workflows       = [];     // list from API
let nodeConfigs     = {};     // nodeId → config object
let _saveTimeout    = null;

// ============================================================
// Init
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  initEditor();
  bindTopbar();
  bindSidebar();
  bindPropsPanel();
  bindModals();
  loadWorkflows();
});

// ============================================================
// Drawflow editor
// ============================================================
function initEditor() {
  const container = document.getElementById('drawflow');
  editor = new Drawflow(container);
  editor.reroute = true;
  editor.reroute_fix_curvature = true;
  editor.force_first_input = false;
  editor.start();

  editor.on('nodeSelected', id => selectNode(id));
  editor.on('nodeUnselected', () => deselectNode());
  editor.on('nodeRemoved',  () => { scheduleSave(); deselectNode(); });
  editor.on('connectionCreated', () => scheduleSave());
  editor.on('connectionRemoved', () => scheduleSave());
  editor.on('nodeMoved', () => scheduleSave());

  // Drop from palette
  const canvas = document.getElementById('canvas-wrap');
  canvas.addEventListener('dragover', e => e.preventDefault());
  canvas.addEventListener('drop', e => {
    e.preventDefault();
    const type = e.dataTransfer.getData('node-type');
    if (!type || !currentWfId) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    addNode(type, x, y);
  });
}

function addNode(type, x, y) {
  const def = NODE_DEFS[type];
  if (!def) return;
  const config = def.defaultConfig();
  const nodeId = editor.addNode(
    type,
    def.inputs,
    def.outputs,
    x, y,
    type,
    {},
    def.html(),
  );
  nodeConfigs[nodeId] = config;
  def.updateNodePreview?.(nodeId, config, editor);
  scheduleSave();
}

// ============================================================
// Node selection → properties panel
// ============================================================
function selectNode(id) {
  selectedNodeId = id;
  const nodeData = editor.getNodeFromId(id);
  const type = nodeData.name;
  const def  = NODE_DEFS[type];
  if (!def) return;

  const config = nodeConfigs[id] || def.defaultConfig();
  nodeConfigs[id] = config;

  openPropsPanel(def.label, def.renderProps(config));
  def.afterRender?.(config, () => {
    const updated = def.readProps(config);
    nodeConfigs[id] = updated;
    def.updateNodePreview?.(id, updated, editor);
    scheduleSave();
  });
}

function deselectNode() {
  if (selectedNodeId !== null) {
    saveCurrentProps();
  }
  selectedNodeId = null;
  closePropsPanel();
}

function saveCurrentProps() {
  if (selectedNodeId === null) return;
  const nodeData = editor.getNodeFromId(selectedNodeId);
  if (!nodeData) return;
  const def = NODE_DEFS[nodeData.name];
  if (!def) return;
  const updated = def.readProps(nodeConfigs[selectedNodeId] || def.defaultConfig());
  nodeConfigs[selectedNodeId] = updated;
  def.updateNodePreview?.(selectedNodeId, updated, editor);
}

// ============================================================
// Auto-save
// ============================================================
function scheduleSave() {
  clearTimeout(_saveTimeout);
  _saveTimeout = setTimeout(() => saveGraph(), 800);
}

async function saveGraph() {
  if (!currentWfId) return;
  saveCurrentProps();

  const drawflowData = editor.export();
  const homeNodes = drawflowData.drawflow?.Home?.data || {};

  const nodes = Object.entries(homeNodes).map(([id, n]) => ({
    id:      String(id),
    type:    n.name,
    label:   n.name,
    pos_x:   n.pos_x,
    pos_y:   n.pos_y,
    config:  nodeConfigs[id] || {},
  }));

  const edges = [];
  Object.entries(homeNodes).forEach(([srcId, n]) => {
    Object.entries(n.outputs || {}).forEach(([outKey, out]) => {
      (out.connections || []).forEach(conn => {
        edges.push({
          id:             `${srcId}_${conn.node}_${outKey}_${conn.output}`,
          source_node_id: String(srcId),
          target_node_id: String(conn.node),
          source_output:  outKey,
          target_input:   conn.output,
        });
      });
    });
  });

  try {
    await api('POST', `/api/workflows/${currentWfId}/graph`, { nodes, edges });
  } catch (e) {
    toast('Auto-save failed: ' + e.message, 'error');
  }
}

// ============================================================
// Load graph into editor
// ============================================================
async function loadGraph(wfId) {
  const data = await api('GET', `/api/workflows/${wfId}/graph`);
  editor.clear();
  nodeConfigs = {};

  const nodeMap = {};  // server id → drawflow id

  // Add nodes
  for (const n of (data.nodes || [])) {
    const def = NODE_DEFS[n.type];
    if (!def) continue;
    const dfId = editor.addNode(
      n.type,
      def.inputs,
      def.outputs,
      n.pos_x, n.pos_y,
      n.type,
      {},
      def.html(),
    );
    nodeMap[n.id] = dfId;
    nodeConfigs[dfId] = n.config || def.defaultConfig();
    def.updateNodePreview?.(dfId, nodeConfigs[dfId], editor);
  }

  // Add edges
  for (const e of (data.edges || [])) {
    const srcDf = nodeMap[e.source_node_id];
    const tgtDf = nodeMap[e.target_node_id];
    if (srcDf && tgtDf) {
      try {
        editor.addConnection(srcDf, tgtDf, e.source_output, e.target_input);
      } catch (_) {}
    }
  }
}

// ============================================================
// Workflow list (left sidebar)
// ============================================================
async function loadWorkflows() {
  workflows = await api('GET', '/api/workflows/');
  renderWorkflowList();
  if (workflows.length > 0 && !currentWfId) {
    openWorkflow(workflows[0].id, workflows[0].name);
  }
}

function renderWorkflowList() {
  const list = document.getElementById('workflow-list');
  if (!list) return;
  list.innerHTML = '';
  if (workflows.length === 0) {
    list.innerHTML = '<div style="padding:8px 4px;font-size:12px;color:var(--text-muted)">No workflows yet</div>';
    return;
  }
  workflows.forEach(wf => {
    const div = document.createElement('div');
    div.className = 'wf-item' + (wf.id === currentWfId ? ' active' : '');
    div.innerHTML = `
      <span class="wf-item-name" title="${esc(wf.name)}">${esc(wf.name)}</span>
      <span class="wf-item-del" title="Delete" data-id="${wf.id}">🗑</span>
    `;
    div.addEventListener('click', e => {
      if (e.target.classList.contains('wf-item-del')) return;
      openWorkflow(wf.id, wf.name);
    });
    div.querySelector('.wf-item-del').addEventListener('click', () => confirmDelete(wf.id, wf.name));
    list.appendChild(div);
  });
}

async function openWorkflow(id, name) {
  currentWfId   = id;
  currentWfName = name;
  document.querySelector('#topbar .wf-name').textContent = name;
  renderWorkflowList();
  await loadGraph(id);
  closePropsPanel();
}

// ============================================================
// Topbar bindings
// ============================================================
function bindTopbar() {
  // Rename on click
  document.querySelector('#topbar .wf-name')?.addEventListener('click', () => {
    if (!currentWfId) return;
    openRenameModal(currentWfName);
  });

  document.getElementById('btn-save')?.addEventListener('click', async () => {
    await saveGraph();
    toast('Saved', 'success');
  });

  document.getElementById('btn-preview')?.addEventListener('click', previewScript);
  document.getElementById('btn-build')?.addEventListener('click', buildExe);
}

// ============================================================
// Sidebar
// ============================================================
function bindSidebar() {
  document.getElementById('btn-new-wf')?.addEventListener('click', () => openNewWfModal());

  document.querySelectorAll('.palette-node').forEach(el => {
    el.setAttribute('draggable', 'true');
    el.addEventListener('dragstart', e => {
      e.dataTransfer.setData('node-type', el.dataset.type);
    });
  });
}

// ============================================================
// Properties panel
// ============================================================
function bindPropsPanel() {
  document.getElementById('props-close')?.addEventListener('click', () => {
    saveCurrentProps();
    scheduleSave();
    closePropsPanel();
  });
}

function openPropsPanel(title, html) {
  document.getElementById('props-title').textContent = title;
  document.getElementById('props-body').innerHTML = html;
  document.getElementById('props-panel').classList.remove('hidden');
}

function closePropsPanel() {
  document.getElementById('props-panel').classList.add('hidden');
}

// ============================================================
// Preview script
// ============================================================
async function previewScript() {
  if (!currentWfId) return toast('Open a workflow first', 'info');
  await saveGraph();
  try {
    const data = await api('POST', `/api/workflows/${currentWfId}/preview`);
    openBuildLogModal('Generated Python Script', data.script, false);
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ============================================================
// Build EXE
// ============================================================
async function buildExe() {
  if (!currentWfId) return toast('Open a workflow first', 'info');
  await saveGraph();

  const btn = document.getElementById('btn-build');
  btn.disabled = true;
  btn.textContent = 'Building…';
  toast('Building .exe — this may take a minute…', 'info');

  try {
    const data = await api('POST', `/api/workflows/${currentWfId}/build`);
    btn.disabled = false;
    btn.textContent = 'Generate EXE';
    openBuildLogModal('Build Successful ✓', data.log, true, data.download_url);
    toast('EXE built successfully!', 'success');
  } catch (e) {
    btn.disabled = false;
    btn.textContent = 'Generate EXE';
    openBuildLogModal('Build Failed', e.detail || e.message, false);
    toast('Build failed: ' + e.message, 'error');
  }
}

// ============================================================
// Modals
// ============================================================
function bindModals() {
  // New workflow modal
  document.getElementById('modal-new-wf-cancel')?.addEventListener('click', () => closeModal('modal-new-wf'));
  document.getElementById('modal-new-wf-create')?.addEventListener('click', createWorkflow);
  document.getElementById('modal-new-wf-name')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') createWorkflow();
  });

  // Rename modal
  document.getElementById('modal-rename-cancel')?.addEventListener('click', () => closeModal('modal-rename'));
  document.getElementById('modal-rename-ok')?.addEventListener('click', renameWorkflow);
  document.getElementById('modal-rename-input')?.addEventListener('keydown', e => {
    if (e.key === 'Enter') renameWorkflow();
  });

  // Delete confirm modal
  document.getElementById('modal-del-cancel')?.addEventListener('click', () => closeModal('modal-del'));
  document.getElementById('modal-del-ok')?.addEventListener('click', deleteWorkflow);

  // Build log modal
  document.getElementById('modal-log-close')?.addEventListener('click', () => closeModal('modal-log'));

  // Close on backdrop click
  document.querySelectorAll('.modal-backdrop').forEach(bd => {
    bd.addEventListener('click', e => { if (e.target === bd) bd.classList.add('hidden'); });
  });
}

function openModal(id)  { document.getElementById(id)?.classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id)?.classList.add('hidden'); }

// New workflow
function openNewWfModal() {
  document.getElementById('modal-new-wf-name').value = '';
  document.getElementById('modal-new-wf-desc').value = '';
  openModal('modal-new-wf');
  setTimeout(() => document.getElementById('modal-new-wf-name')?.focus(), 50);
}

async function createWorkflow() {
  const name = document.getElementById('modal-new-wf-name')?.value.trim();
  if (!name) return toast('Enter a workflow name', 'error');
  const description = document.getElementById('modal-new-wf-desc')?.value.trim();
  closeModal('modal-new-wf');
  try {
    const wf = await api('POST', '/api/workflows/', { name, description });
    workflows.unshift(wf);
    renderWorkflowList();
    openWorkflow(wf.id, wf.name);
    toast(`Workflow "${name}" created`, 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

// Rename
function openRenameModal(current) {
  document.getElementById('modal-rename-input').value = current;
  openModal('modal-rename');
  setTimeout(() => document.getElementById('modal-rename-input')?.focus(), 50);
}

async function renameWorkflow() {
  if (!currentWfId) return;
  const name = document.getElementById('modal-rename-input')?.value.trim();
  if (!name) return toast('Enter a name', 'error');
  closeModal('modal-rename');
  try {
    const updated = await api('PUT', `/api/workflows/${currentWfId}`, { name });
    currentWfName = updated.name;
    document.querySelector('#topbar .wf-name').textContent = updated.name;
    const wf = workflows.find(w => w.id === currentWfId);
    if (wf) wf.name = updated.name;
    renderWorkflowList();
    toast('Renamed', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

// Delete
let _pendingDeleteId = null;
function confirmDelete(id, name) {
  _pendingDeleteId = id;
  document.getElementById('modal-del-name').textContent = name;
  openModal('modal-del');
}

async function deleteWorkflow() {
  if (!_pendingDeleteId) return;
  const id = _pendingDeleteId;
  _pendingDeleteId = null;
  closeModal('modal-del');
  try {
    await api('DELETE', `/api/workflows/${id}`);
    workflows = workflows.filter(w => w.id !== id);
    if (currentWfId === id) {
      currentWfId = null;
      currentWfName = '';
      editor.clear();
      nodeConfigs = {};
      document.querySelector('#topbar .wf-name').textContent = '—';
      closePropsPanel();
    }
    renderWorkflowList();
    if (workflows.length > 0 && !currentWfId) openWorkflow(workflows[0].id, workflows[0].name);
    toast('Workflow deleted', 'success');
  } catch (e) {
    toast(e.message, 'error');
  }
}

// Build log
function openBuildLogModal(title, content, success, downloadUrl = null) {
  document.getElementById('modal-log-title').textContent = title;
  document.getElementById('build-log-content').textContent = content;
  const dlBtn = document.getElementById('modal-log-download');
  if (downloadUrl && success) {
    dlBtn.style.display = 'inline-block';
    dlBtn.onclick = () => { window.location.href = downloadUrl; };
  } else {
    dlBtn.style.display = 'none';
  }
  openModal('modal-log');
}

// ============================================================
// API helper
// ============================================================
async function api(method, url, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(json.error || `HTTP ${res.status}`);
    err.detail = json.log || null;
    throw err;
  }
  return json;
}

// ============================================================
// Toast
// ============================================================
function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ============================================================
// Util
// ============================================================
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
