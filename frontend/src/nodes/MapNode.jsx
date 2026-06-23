import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';

const INPUT_MODES = [
  { value: 'variable', label: 'Local variable (${VAR})' },
  { value: 'secret', label: 'Secret (#{SECRET})' },
  { value: 'global', label: 'Global (@{GLOBAL})' },
];

const DATA_TYPES = [
  { value: 'string', label: 'String' },
  { value: 'number', label: 'Number' },
  { value: 'boolean', label: 'Boolean' },
];

const OPERATORS_BY_TYPE = {
  string: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not equals' },
    { value: 'contains', label: 'Contains' },
    { value: 'starts_with', label: 'Starts with' },
    { value: 'ends_with', label: 'Ends with' },
    { value: 'is_empty', label: 'Is empty' },
    { value: 'is_not_empty', label: 'Is not empty' },
  ],
  number: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not equals' },
    { value: 'greater_than', label: 'Greater than' },
    { value: 'less_than', label: 'Less than' },
    { value: 'greater_or_equal', label: 'Greater or equal' },
    { value: 'less_or_equal', label: 'Less or equal' },
  ],
  boolean: [
    { value: 'is_true', label: 'Is true' },
    { value: 'is_false', label: 'Is false' },
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not equals' },
  ],
};

const VALUE_MODES = [
  { value: 'literal', label: 'Literal' },
  { value: 'variable', label: 'Local variable' },
  { value: 'secret', label: 'Secret' },
  { value: 'global', label: 'Global' },
];

const UNARY_OPERATORS = new Set(['is_empty', 'is_not_empty', 'is_true', 'is_false']);

function normalizeInputMode(value) {
  const mode = String(value || 'variable').toLowerCase();
  if (mode === 'secret' || mode === 'global') return mode;
  return 'variable';
}

function normalizeDataType(value) {
  const type = String(value || 'string').toLowerCase();
  if (type === 'number' || type === 'boolean') return type;
  return 'string';
}

function normalizeValueMode(value) {
  const mode = String(value || 'literal').toLowerCase();
  if (mode === 'variable' || mode === 'secret' || mode === 'global') return mode;
  return 'literal';
}

function getOperators(dataType) {
  return OPERATORS_BY_TYPE[dataType] || OPERATORS_BY_TYPE.string;
}

function getDefaultRule() {
  return {
    operator: 'equals',
    compare_value: '',
    value_mode: 'literal',
    mapped_value: '',
  };
}

function normalizeRule(rawRule, dataType) {
  const safe = rawRule && typeof rawRule === 'object' ? rawRule : {};
  const operators = getOperators(dataType);
  const allowed = new Set(operators.map((op) => op.value));
  const operator = allowed.has(String(safe.operator || '')) ? String(safe.operator) : operators[0].value;
  return {
    operator,
    compare_value: String(safe.compare_value || ''),
    value_mode: normalizeValueMode(safe.value_mode),
    mapped_value: String(safe.mapped_value || ''),
  };
}

function normalizeRules(config, dataType) {
  const raw = Array.isArray(config.rules) ? config.rules : [];
  if (!raw.length) return [normalizeRule(getDefaultRule(), dataType)];
  return raw.map((rule) => normalizeRule(rule, dataType));
}

function normalizeDefault(config) {
  const raw = config.default;
  if (!raw || typeof raw !== 'object') return null;
  return {
    value_mode: normalizeValueMode(raw.value_mode),
    mapped_value: String(raw.mapped_value || ''),
  };
}

export default function MapNode({ data }) {
  const rules = Array.isArray(data.config?.rules) ? data.config.rules : [];
  const outputKey = data.config?.output_key || 'mapped_value';
  const inputSource = data.config?.input_source || '${value}';

  return (
    <BaseNode icon="🗺️" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div className="truncate"><span className="text-muted-foreground">in:</span> {inputSource}</div>
        <div className="truncate"><span className="text-muted-foreground">out:</span> {outputKey}</div>
        <div>{rules.length} rule{rules.length !== 1 ? 's' : ''}</div>
      </div>
    </BaseNode>
  );
}

export function MapPropsForm({ config, onChange }) {
  const inputValueMode = normalizeInputMode(config.input_value_mode);
  const inputDataType = normalizeDataType(config.input_data_type);
  const rules = normalizeRules(config, inputDataType);
  const defaultValue = normalizeDefault(config);
  const useDefault = defaultValue !== null;

  const updateConfig = (patch) => {
    const next = {
      ...config,
      ...patch,
    };
    onChange(next);
  };

  const updateRules = (nextRules) => {
    updateConfig({ rules: nextRules });
  };

  const updateRule = (idx, patch) => {
    const next = rules.map((rule, i) => {
      if (i !== idx) return rule;
      const merged = { ...rule, ...patch };
      const operators = getOperators(inputDataType);
      const allowed = new Set(operators.map((op) => op.value));
      if (!allowed.has(merged.operator)) {
        merged.operator = operators[0].value;
      }
      merged.value_mode = normalizeValueMode(merged.value_mode);
      return merged;
    });
    updateRules(next);
  };

  const addRule = () => {
    updateRules([...rules, normalizeRule(getDefaultRule(), inputDataType)]);
  };

  const removeRule = (idx) => {
    const next = rules.filter((_, i) => i !== idx);
    updateRules(next.length ? next : [normalizeRule(getDefaultRule(), inputDataType)]);
  };

  const changeInputType = (nextTypeRaw) => {
    const nextType = normalizeDataType(nextTypeRaw);
    const operators = getOperators(nextType);
    const allowed = new Set(operators.map((op) => op.value));
    const nextRules = rules.map((rule) => ({
      ...rule,
      operator: allowed.has(rule.operator) ? rule.operator : operators[0].value,
    }));
    updateConfig({ input_data_type: nextType, rules: nextRules });
  };

  const toggleDefault = (checked) => {
    if (checked === true) {
      updateConfig({ default: { value_mode: 'literal', mapped_value: '' } });
      return;
    }
    updateConfig({ default: null });
  };

  const updateDefault = (patch) => {
    const current = defaultValue || { value_mode: 'literal', mapped_value: '' };
    updateConfig({
      default: {
        ...current,
        ...patch,
      },
    });
  };

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label className="text-xs font-medium">Output variable</Label>
        <Input
          placeholder="mapped_value"
          value={config.output_key || ''}
          onChange={(e) => updateConfig({ output_key: e.target.value })}
        />
      </div>

      <div className="prop-group">
        <Label className="text-xs font-medium">Input source mode</Label>
        <select
          value={inputValueMode}
          onChange={(e) => updateConfig({ input_value_mode: normalizeInputMode(e.target.value) })}
          className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
        >
          {INPUT_MODES.map((mode) => (
            <option key={mode.value} value={mode.value}>{mode.label}</option>
          ))}
        </select>
      </div>

      <div className="prop-group">
        <Label className="text-xs font-medium">Input variable to analyze</Label>
        <Input
          placeholder={
            inputValueMode === 'secret'
              ? '#{SECRET_NAME} or SECRET_NAME'
              : inputValueMode === 'global'
              ? '@{GLOBAL_NAME} or GLOBAL_NAME'
              : '${LOCAL_NAME} or LOCAL_NAME'
          }
          value={config.input_source || ''}
          onChange={(e) => updateConfig({ input_source: e.target.value })}
        />
      </div>

      <div className="prop-group">
        <Label className="text-xs font-medium">Input data type</Label>
        <select
          value={inputDataType}
          onChange={(e) => changeInputType(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
        >
          {DATA_TYPES.map((type) => (
            <option key={type.value} value={type.value}>{type.label}</option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <Label>Rules</Label>
        {rules.map((rule, idx) => {
          const operators = getOperators(inputDataType);
          const isUnary = UNARY_OPERATORS.has(rule.operator);

          return (
            <div key={idx} className="rounded-md border border-border p-2 space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs text-muted-foreground">Rule {idx + 1}</Label>
                <button
                  type="button"
                  onClick={() => removeRule(idx)}
                  className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
                  title="Remove"
                  disabled={rules.length <= 1}
                >
                  ×
                </button>
              </div>

              <div className="prop-group">
                <Label className="text-xs font-medium">Condition</Label>
                <select
                  value={rule.operator}
                  onChange={(e) => updateRule(idx, { operator: e.target.value })}
                  className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
                >
                  {operators.map((op) => (
                    <option key={op.value} value={op.value}>{op.label}</option>
                  ))}
                </select>
              </div>

              {!isUnary && (
                <div className="prop-group">
                  <Label className="text-xs font-medium">Comparison value</Label>
                  <Input
                    placeholder={inputDataType === 'boolean' ? 'true/false or ${VAR}' : 'literal or ${VAR}/@{GLOBAL}/#{SECRET}'}
                    value={rule.compare_value || ''}
                    onChange={(e) => updateRule(idx, { compare_value: e.target.value })}
                  />
                </div>
              )}

              <div className="prop-group">
                <Label className="text-xs font-medium">Mapped value mode</Label>
                <select
                  value={normalizeValueMode(rule.value_mode)}
                  onChange={(e) => updateRule(idx, { value_mode: normalizeValueMode(e.target.value) })}
                  className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
                >
                  {VALUE_MODES.map((mode) => (
                    <option key={mode.value} value={mode.value}>{mode.label}</option>
                  ))}
                </select>
              </div>

              <div className="prop-group">
                <Label className="text-xs font-medium">Mapped value</Label>
                <Input
                  placeholder={
                    normalizeValueMode(rule.value_mode) === 'variable'
                      ? '${TARGET_VAR} or TARGET_VAR'
                      : normalizeValueMode(rule.value_mode) === 'secret'
                      ? '#{TARGET_SECRET} or TARGET_SECRET'
                      : normalizeValueMode(rule.value_mode) === 'global'
                      ? '@{TARGET_GLOBAL} or TARGET_GLOBAL'
                      : 'literal value'
                  }
                  value={rule.mapped_value || ''}
                  onChange={(e) => updateRule(idx, { mapped_value: e.target.value })}
                />
              </div>
            </div>
          );
        })}

        <Button variant="outline" size="sm" className="w-full mt-1" onClick={addRule}>
          + Add rule
        </Button>
      </div>

      <div className="rounded-md border border-border p-2 space-y-2">
        <div className="flex items-center gap-2">
          <Checkbox id="map-default-enabled" checked={useDefault} onCheckedChange={toggleDefault} />
          <Label htmlFor="map-default-enabled" className="text-xs font-medium cursor-pointer">
            Use default value when no rule matches
          </Label>
        </div>

        {useDefault && (
          <div className="space-y-2">
            <div className="prop-group">
              <Label className="text-xs font-medium">Default mapped mode</Label>
              <select
                value={normalizeValueMode(defaultValue?.value_mode)}
                onChange={(e) => updateDefault({ value_mode: normalizeValueMode(e.target.value) })}
                className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
              >
                {VALUE_MODES.map((mode) => (
                  <option key={mode.value} value={mode.value}>{mode.label}</option>
                ))}
              </select>
            </div>
            <div className="prop-group">
              <Label className="text-xs font-medium">Default mapped value</Label>
              <Input
                placeholder="fallback value"
                value={defaultValue?.mapped_value || ''}
                onChange={(e) => updateDefault({ mapped_value: e.target.value })}
              />
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 pt-2">
        <Checkbox
          id="include-input-fields-map"
          checked={config.include_other_input_fields || false}
          onCheckedChange={(checked) =>
            updateConfig({ include_other_input_fields: checked === true })
          }
        />
        <Label
          htmlFor="include-input-fields-map"
          className="text-sm text-muted-foreground cursor-pointer"
        >
          Include Other Input Fields
        </Label>
      </div>

      <div className="rounded-md border border-border p-2">
        <p className="text-[11px] text-muted-foreground">
          Input supports local <code>{'${VAR}'}</code>, secret <code>{'#{SECRET}'}</code>, and global <code>{'@{GLOBAL}'}</code>. Conditions adapt to selected data type.
        </p>
      </div>
    </div>
  );
}
