import { Handle, Position } from 'reactflow';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';

const OPERATORS_BY_TYPE = {
  string: [
    { value: 'equals', label: 'Equals' },
    { value: 'not_equals', label: 'Not equals' },
    { value: 'contains', label: 'Contains' },
    { value: 'not_contains', label: 'Not contains' },
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
  ],
  object: [
    { value: 'exists', label: 'Exists' },
    { value: 'not_exists', label: 'Not exists' },
    { value: 'has_property', label: 'Has property' },
    { value: 'not_has_property', label: 'Not has property' },
  ],
  array: [
    { value: 'is_empty', label: 'Is empty' },
    { value: 'is_not_empty', label: 'Is not empty' },
    { value: 'length_equals', label: 'Length equals' },
    { value: 'length_greater_than', label: 'Length greater than' },
    { value: 'length_less_than', label: 'Length less than' },
  ],
};

const UNARY_OPERATORS = new Set(['is_true', 'is_false', 'is_empty', 'is_not_empty', 'exists', 'not_exists']);

function normalizeType(value) {
  const t = String(value || 'string').toLowerCase();
  if (t === 'number' || t === 'boolean' || t === 'object' || t === 'array') return t;
  return 'string';
}

function getAllowedOperators(dataType) {
  return OPERATORS_BY_TYPE[dataType] || OPERATORS_BY_TYPE.string;
}

function getDefaultCondition() {
  return {
    join: 'and',
    input: '${variable}',
    data_type: 'string',
    operator: 'equals',
    compare_value: '',
  };
}

function getConditions(config) {
  const raw = Array.isArray(config.conditions) ? config.conditions : null;
  if (raw && raw.length > 0) {
    return raw.map((item, idx) => {
      const cond = item && typeof item === 'object' ? item : {};
      const dataType = normalizeType(cond.data_type);
      const ops = getAllowedOperators(dataType);
      const allowed = new Set(ops.map(op => op.value));
      const operator = allowed.has(cond.operator) ? cond.operator : ops[0].value;
      return {
        join: idx === 0 ? 'and' : (String(cond.join || 'and').toLowerCase() === 'or' ? 'or' : 'and'),
        input: cond.input || '',
        data_type: dataType,
        operator,
        compare_value: cond.compare_value || '',
      };
    });
  }

  const legacyType = normalizeType(config.data_type);
  const legacyOps = getAllowedOperators(legacyType);
  const legacyAllowed = new Set(legacyOps.map(op => op.value));
  const legacyOperator = legacyAllowed.has(config.operator) ? config.operator : legacyOps[0].value;
  return [{
    join: 'and',
    input: config.input || '',
    data_type: legacyType,
    operator: legacyOperator,
    compare_value: config.compare_value || '',
  }];
}

export default function IfNode({ data }) {
  const conditions = Array.isArray(data.config?.conditions) ? data.config.conditions : [];
  return (
    <div style={{ minWidth: 220, position: 'relative' }}>
      <Handle type="target" position={Position.Left} id="input_1" />

      <div className="node-title-box">
        <span>🔀</span>
        <span>{data.instanceName || 'IF'}</span>
      </div>

      <div className="node-body space-y-1">
        <div className="text-xs text-muted-foreground">Condition</div>
        <div className="font-mono text-[11px] truncate">
          {conditions.length > 0 ? `${conditions.length} condition${conditions.length !== 1 ? 's' : ''}` : (data.config?.input || '${variable}')}
        </div>
      </div>

      <Handle type="source" position={Position.Right} id="true" style={{ top: '35%' }} />
      <Handle type="source" position={Position.Right} id="false" style={{ top: '70%' }} />

      <span className="absolute right-2 text-[10px] text-emerald-600" style={{ top: '27%' }}>True</span>
      <span className="absolute right-2 text-[10px] text-rose-600" style={{ top: '62%' }}>False</span>
    </div>
  );
}

export function IfPropsForm({ config, onChange }) {
  const conditions = getConditions(config);

  const updateConditions = (nextConditions) => {
    const normalized = nextConditions.map((cond, idx) => ({
      ...getDefaultCondition(),
      ...cond,
      join: idx === 0 ? 'and' : (String(cond.join || 'and').toLowerCase() === 'or' ? 'or' : 'and'),
    }));

    const first = normalized[0] || getDefaultCondition();
    onChange({
      ...config,
      input: first.input,
      data_type: first.data_type,
      operator: first.operator,
      compare_value: first.compare_value,
      conditions: normalized,
    });
  };

  const updateCondition = (idx, patch) => {
    const next = conditions.map((cond, i) => {
      if (i !== idx) return cond;
      const merged = { ...cond, ...patch };
      const nextType = normalizeType(merged.data_type);
      const ops = getAllowedOperators(nextType);
      const allowed = new Set(ops.map(op => op.value));
      const nextOperator = allowed.has(merged.operator) ? merged.operator : ops[0].value;
      return {
        ...merged,
        data_type: nextType,
        operator: nextOperator,
      };
    });
    updateConditions(next);
  };

  const addCondition = () => {
    updateConditions([...conditions, { ...getDefaultCondition(), join: 'and' }]);
  };

  const removeCondition = (idx) => {
    const next = conditions.filter((_, i) => i !== idx);
    updateConditions(next.length ? next : [getDefaultCondition()]);
  };


  return (
    <div className="space-y-3">
      {conditions.map((cond, idx) => {
        const dataType = normalizeType(cond.data_type);
        const allowedOperators = getAllowedOperators(dataType);
        const isUnary = UNARY_OPERATORS.has(cond.operator);

        return (
          <div key={idx} className="rounded-md border border-border p-2 space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs text-muted-foreground">Condition {idx + 1}</Label>
              <button
                type="button"
                onClick={() => removeCondition(idx)}
                className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
                title="Remove"
                disabled={conditions.length <= 1}
              >
                ×
              </button>
            </div>

            {idx > 0 && (
              <div className="prop-group">
                <Label className="text-xs font-medium">Join with previous</Label>
                <select
                  value={cond.join === 'or' ? 'or' : 'and'}
                  onChange={e => updateCondition(idx, { join: e.target.value === 'or' ? 'or' : 'and' })}
                  className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
                >
                  <option value="and">AND</option>
                  <option value="or">OR</option>
                </select>
              </div>
            )}

            <div className="prop-group">
              <Label className="text-xs font-medium">Variable to evaluate</Label>
              <Input
                placeholder="${VARIABLE}"
                value={cond.input || ''}
                onChange={e => updateCondition(idx, { input: e.target.value })}
              />
            </div>

            <div className="prop-group">
              <Label className="text-xs font-medium">Data type</Label>
              <select
                value={dataType}
                onChange={e => {
                  const nextType = normalizeType(e.target.value);
                  const nextOps = getAllowedOperators(nextType);
                  updateCondition(idx, { data_type: nextType, operator: nextOps[0].value });
                }}
                className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
              >
                <option value="string">String</option>
                <option value="number">Number</option>
                <option value="boolean">Boolean</option>
                <option value="object">Object</option>
                <option value="array">Array</option>
              </select>
            </div>

            <div className="prop-group">
              <Label className="text-xs font-medium">Condition</Label>
              <select
                value={cond.operator}
                onChange={e => updateCondition(idx, { operator: e.target.value })}
                className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
              >
                {allowedOperators.map(op => (
                  <option key={op.value} value={op.value}>{op.label}</option>
                ))}
              </select>
            </div>

            {!isUnary && (
              <div className="prop-group">
                <Label className="text-xs font-medium">Comparison value</Label>
                <Input
                  placeholder={dataType === 'object' ? 'property or ${VARIABLE}' : 'literal or ${VARIABLE}'}
                  value={cond.compare_value || ''}
                  onChange={e => updateCondition(idx, { compare_value: e.target.value })}
                />
              </div>
            )}
          </div>
        );
      })}

      <Button variant="outline" size="sm" className="w-full mt-1" onClick={addCondition}>
        + Add condition
      </Button>

      <div className="rounded-md border border-border p-2">
        <p className="text-[11px] text-muted-foreground">
          Use <code>${'{'}VARIABLE{'}'}</code> to resolve item values at runtime.
        </p>
      </div>
    </div>
  );
}
