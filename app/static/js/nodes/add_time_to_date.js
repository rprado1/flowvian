// ============================================================
// Add Time to Date Node
// ============================================================

const AddTimeToDateNode = {
  type: 'add_time_to_date',
  label: 'Add Time to Date',
  icon: '⏩',
  description: 'Adds days/hours/minutes/seconds to a datetime variable',
  inputs: 1,
  outputs: 1,

  html() {
    return `
      <div class="title-box"><span>${this.icon}</span> ${this.label}</div>
      <div class="box" style="font-size:11px;color:#8899aa;">
        <span class="atd-input-var">?</span> → <span class="atd-output-var">new_date</span>
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
        <input type="text" id="prop-atd-input-var"
               value="${_esc(String(config.input_var ?? ''))}"
               placeholder="e.g. current_date_utc" />
      </div>
      <div class="prop-group">
        <label>Days to add</label>
        <input type="number" id="prop-atd-days" value="${config.days ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Hours to add</label>
        <input type="number" id="prop-atd-hours" value="${config.hours ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Minutes to add</label>
        <input type="number" id="prop-atd-minutes" value="${config.minutes ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Seconds to add</label>
        <input type="number" id="prop-atd-seconds" value="${config.seconds ?? 0}" step="1" />
      </div>
      <div class="prop-group">
        <label>Output variable name</label>
        <input type="text" id="prop-atd-output-var"
               value="${_esc(String(config.output_var ?? 'new_date'))}"
               placeholder="new_date" />
      </div>
    `;
  },

  readProps(config) {
    return {
      ...config,
      input_var:  (document.getElementById('prop-atd-input-var')?.value.trim())  || '',
      days:       parseFloat(document.getElementById('prop-atd-days')?.value)    || 0,
      hours:      parseFloat(document.getElementById('prop-atd-hours')?.value)   || 0,
      minutes:    parseFloat(document.getElementById('prop-atd-minutes')?.value) || 0,
      seconds:    parseFloat(document.getElementById('prop-atd-seconds')?.value) || 0,
      output_var: (document.getElementById('prop-atd-output-var')?.value.trim()) || 'new_date',
    };
  },

  updateNodePreview(nodeId, config) {
    const inputEl  = document.querySelector(`#node-${nodeId} .atd-input-var`);
    const outputEl = document.querySelector(`#node-${nodeId} .atd-output-var`);
    if (inputEl)  inputEl.textContent  = config.input_var  || '?';
    if (outputEl) outputEl.textContent = config.output_var || 'new_date';
  },
};

// Note: _esc() is defined in set_variables.js (loaded before this file)
