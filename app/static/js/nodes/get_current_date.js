// ============================================================
// Get Current Date UTC Node
// ============================================================

const GetCurrentDateUTCNode = {
  type: 'get_current_date_utc',
  label: 'Get Current Date UTC',
  icon: '📅',
  description: 'Captures datetime.now(UTC) into a variable',
  inputs: 1,
  outputs: 1,

  html() {
    return `
      <div class="title-box"><span>${this.icon}</span> ${this.label}</div>
      <div class="box" style="font-size:11px;color:#8899aa;">→ <span class="date-var">current_date_utc</span></div>
    `;
  },

  defaultConfig() {
    return { output_var: 'current_date_utc' };
  },

  renderProps(config) {
    return `
      <div class="prop-group">
        <label>Output variable name</label>
        <input type="text" id="prop-output-var" value="${config.output_var ?? 'current_date_utc'}" placeholder="current_date_utc" />
      </div>
    `;
  },

  readProps(config) {
    const output_var = (document.getElementById('prop-output-var')?.value.trim()) || 'current_date_utc';
    return { ...config, output_var };
  },

  updateNodePreview(nodeId, config) {
    const el = document.querySelector(`#node-${nodeId} .date-var`);
    if (el) el.textContent = config.output_var || 'current_date_utc';
  },
};
