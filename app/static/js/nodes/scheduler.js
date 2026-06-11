// ============================================================
// Scheduler Node — Drawflow registration & properties panel
// ============================================================

const SchedulerNode = {
  type: 'scheduler',
  label: 'Scheduler',
  icon: '⏱',
  description: 'Runs the workflow on a time interval',
  inputs: 0,
  outputs: 1,

  /** HTML rendered inside the Drawflow node card */
  html() {
    return `
      <div class="title-box"><span>${this.icon}</span> ${this.label}</div>
      <div class="box node-scheduler-preview">Every <span class="sched-val">60</span>s</div>
    `;
  },

  /** Default config when node is first dropped */
  defaultConfig() {
    return { interval: 60, unit: 'seconds' };
  },

  /** Render properties into the right panel #props-body */
  renderProps(config, onChange) {
    return `
      <div class="prop-group">
        <label>Interval</label>
        <input type="number" min="1" step="1" id="prop-interval" value="${config.interval ?? 60}" />
      </div>
      <div class="prop-group">
        <label>Unit</label>
        <select id="prop-unit">
          <option value="seconds"  ${config.unit === 'seconds'  ? 'selected' : ''}>Seconds</option>
          <option value="minutes"  ${config.unit === 'minutes'  ? 'selected' : ''}>Minutes</option>
          <option value="hours"    ${config.unit === 'hours'    ? 'selected' : ''}>Hours</option>
        </select>
      </div>
    `;
  },

  /** Read values from rendered props and return updated config */
  readProps(config) {
    const interval = parseFloat(document.getElementById('prop-interval')?.value) || 60;
    const unit     = document.getElementById('prop-unit')?.value || 'seconds';
    return { ...config, interval, unit };
  },

  /** Update the preview text shown inside the node card */
  updateNodePreview(nodeId, config, editor) {
    const el = document.querySelector(`#node-${nodeId} .sched-val`);
    if (el) el.textContent = `${config.interval} ${config.unit}`;
  },
};
