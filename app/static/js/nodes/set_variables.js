// ============================================================
// Set Variables Node — Drawflow registration & properties panel
// ============================================================

const SetVariablesNode = {
  type: 'set_variables',
  label: 'Set Variables',
  icon: '📦',
  description: 'Assigns key=value pairs into the workflow context',
  inputs: 1,
  outputs: 1,

  html() {
    return `
      <div class="title-box"><span>${this.icon}</span> ${this.label}</div>
      <div class="box node-setvars-preview"><span class="vars-count">0</span> variable(s)</div>
    `;
  },

  defaultConfig() {
    return { variables: [] };
  },

  renderProps(config, onChange) {
    const vars = config.variables || [];
    const rows = vars.map((v, i) => _varRow(i, v.key, v.value)).join('');
    return `
      <div class="prop-group">
        <label>Variables</label>
        <div id="vars-list">${rows}</div>
        <button class="btn btn-outline btn-sm" id="add-var-btn" style="margin-top:6px;width:100%">+ Add variable</button>
      </div>
    `;
  },

  /** Called after renderProps HTML is injected — attach event listeners */
  afterRender(config, onConfigChange) {
    document.getElementById('add-var-btn')?.addEventListener('click', () => {
      const list = document.getElementById('vars-list');
      if (!list) return;
      const idx = list.children.length;
      const row = document.createElement('div');
      row.innerHTML = _varRow(idx, '', '');
      list.appendChild(row.firstElementChild);
      _attachDelListeners(onConfigChange);
    });
    _attachDelListeners(onConfigChange);
  },

  readProps(config) {
    const rows = document.querySelectorAll('#vars-list .var-row');
    const variables = [];
    rows.forEach(row => {
      const key   = row.querySelector('.var-key')?.value.trim()  || '';
      const value = row.querySelector('.var-val')?.value         || '';
      if (key) variables.push({ key, value });
    });
    return { ...config, variables };
  },

  updateNodePreview(nodeId, config) {
    const el = document.querySelector(`#node-${nodeId} .vars-count`);
    if (el) el.textContent = (config.variables || []).length;
  },
};

function _varRow(idx, key, value) {
  return `
    <div class="var-row" data-idx="${idx}">
      <input class="var-key" type="text" placeholder="key"   value="${_esc(key)}"   />
      <input class="var-val" type="text" placeholder="value" value="${_esc(value)}" />
      <button class="var-del" title="Remove">×</button>
    </div>
  `;
}

function _attachDelListeners(onConfigChange) {
  document.querySelectorAll('.var-del').forEach(btn => {
    btn.onclick = () => {
      btn.closest('.var-row').remove();
      if (typeof onConfigChange === 'function') onConfigChange();
    };
  });
}

function _esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
}
