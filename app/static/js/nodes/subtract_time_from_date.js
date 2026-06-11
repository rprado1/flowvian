// ============================================================
// Subtract Time from Date Node
// ============================================================

const SubtractTimeFromDateNode = {
  type: 'subtract_time_from_date',
  label: 'Subtract Time from Date',
  icon: '⏪',
  description: 'Subtracts days/hours/minutes/seconds from a datetime variable',
  inputs: 1,
  outputs: 1,

  html() {
    return `
      <div class="title-box"><span>${this.icon}</span> ${this.label}</div>
      <div class="box" style="font-size:11px;color:#8899aa;">
        <span class="stfd-input-var">?</span> → <span class="stfd-output-var">new_date</span>
      </div>
    `;
  },

  defaultConfig() {
    return {
      input_var: '',
      days: 0,
      hours: 0,
      minutes: 0,
      seconds: 0,
      output_var: 'new_date',
    };
  },

  renderProps(config) {
    return `
      <div class="prop-group">
        <label>Input datetime variable</label>
        <input type="text" id="prop-stfd-input-var"
               value="${_esc(String(config.input_var ?? ''))}"
               placeholder="e.g. current_date_utc" />
      </div>
      <div class="prop-group">
        <label>Days to subtract</label>
        <input type="number" id="prop-stfd-days" value="${config.days ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Hours to subtract</label>
        <input type="number" id="prop-stfd-hours" value="${config.hours ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Minutes to subtract</label>
        <input type="number" id="prop-stfd-minutes" value="${config.minutes ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Seconds to subtract</label>
        <input type="number" id="prop-stfd-seconds" value="${config.seconds ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Output variable name</label>
        <input type="text" id="prop-stfd-output-var"
               value="${_esc(String(config.output_var ?? 'new_date'))}"
               placeholder="new_date" />
      </div>
    `;
  },

  readProps(config) {
    return {
      ...config,
      input_var:  (document.getElementById('prop-stfd-input-var')?.value.trim())  || '',
      days:       parseFloat(document.getElementById('prop-stfd-days')?.value)    || 0,
      hours:      parseFloat(document.getElementById('prop-stfd-hours')?.value)   || 0,
      minutes:    parseFloat(document.getElementById('prop-stfd-minutes')?.value) || 0,
      seconds:    parseFloat(document.getElementById('prop-stfd-seconds')?.value) || 0,
      output_var: (document.getElementById('prop-stfd-output-var')?.value.trim()) || 'new_date',
    };
  },

  updateNodePreview(nodeId, config) {
    const inputEl  = document.querySelector(`#node-${nodeId} .stfd-input-var`);
    const outputEl = document.querySelector(`#node-${nodeId} .stfd-output-var`);
    if (inputEl)  inputEl.textContent  = config.input_var  || '?';
    if (outputEl) outputEl.textContent = config.output_var || 'new_date';
  },
};

// Note: _esc() is defined in set_variables.js (loaded before this file)
