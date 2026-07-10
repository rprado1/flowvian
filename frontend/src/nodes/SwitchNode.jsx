import { useEffect } from 'react';
import { Handle, Position, useUpdateNodeInternals } from 'reactflow';
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

function getDefaultRoute(index = 0) {
  return {
    name: `Route ${index + 1}`,
    condition: {
      input: '${value}',
      data_type: 'string',
      operator: 'equals',
      compare_value: '',
    },
  };
}

function getRoutes(config) {
  const raw = Array.isArray(config.routes) ? config.routes : [];
  if (raw.length === 0) return [getDefaultRoute(0)];

  return raw.map((route, idx) => {
    const safe = route && typeof route === 'object' ? route : {};
    const condRaw = safe.condition && typeof safe.condition === 'object' ? safe.condition : {};
    const dataType = normalizeType(condRaw.data_type);
    const allowed = getAllowedOperators(dataType);
    const allowedSet = new Set(allowed.map(op => op.value));
    const operator = allowedSet.has(condRaw.operator) ? condRaw.operator : allowed[0].value;
    return {
      name: String(safe.name || `Route ${idx + 1}`),
      condition: {
        input: String(condRaw.input || '${value}'),
        data_type: dataType,
        operator,
        compare_value: String(condRaw.compare_value || ''),
      },
    };
  });
}

export default function SwitchNode({ id, data }) {
  const updateNodeInternals = useUpdateNodeInternals();
  const routes = getRoutes(data.config || {});

  useEffect(() => {
    updateNodeInternals(id);
  }, [id, routes.length, updateNodeInternals]);

  const outputHandles = routes.map((route, idx) => {
    const top = ((idx + 1) / (routes.length + 1)) * 100;
    return (
      <div key={`route-${idx}`}>
        <Handle
          type="source"
          position={Position.Right}
          id={`route_${idx + 1}`}
          style={{ top: `${top}%` }}
        />
        <span className="absolute right-2 text-[10px] text-muted-foreground" style={{ top: `calc(${top}% - 8px)` }}>
          {route.name || `Route ${idx + 1}`}
        </span>
      </div>
    );
  });

  return (
    <div style={{ minWidth: 240, minHeight: Math.max(120, 64 + routes.length * 24), position: 'relative' }}>
      <Handle type="target" position={Position.Left} id="input_1" />
      {outputHandles}

      <div className="node-title-box">
        <span>🔀</span>
        <span>{data.instanceName || 'Switch'}</span>
      </div>

      <div className="node-body space-y-1">
        <div className="text-xs text-muted-foreground">Routes</div>
        <div className="font-mono text-[11px] truncate">{routes.length} route{routes.length !== 1 ? 's' : ''}</div>
      </div>
    </div>
  );
}

export function SwitchPropsForm({ config, onChange }) {
  const routes = getRoutes(config);

  const updateRoutes = (nextRoutes) => {
    const normalized = nextRoutes.map((route, idx) => {
      const safe = route && typeof route === 'object' ? route : getDefaultRoute(idx);
      const cond = safe.condition && typeof safe.condition === 'object' ? safe.condition : getDefaultRoute(idx).condition;
      const nextType = normalizeType(cond.data_type);
      const ops = getAllowedOperators(nextType);
      const allowed = new Set(ops.map(op => op.value));
      const nextOperator = allowed.has(cond.operator) ? cond.operator : ops[0].value;
      return {
        name: String(safe.name || `Route ${idx + 1}`),
        condition: {
          input: String(cond.input || '${value}'),
          data_type: nextType,
          operator: nextOperator,
          compare_value: String(cond.compare_value || ''),
        },
      };
    });

    onChange({
      ...config,
      routes: normalized,
      discard_unmatched: true,
    });
  };

  const updateRoute = (idx, patch) => {
    const next = routes.map((route, i) => {
      if (i !== idx) return route;
      return {
        ...route,
        ...patch,
        condition: {
          ...route.condition,
          ...(patch.condition || {}),
        },
      };
    });
    updateRoutes(next);
  };

  const addRoute = () => {
    updateRoutes([...routes, getDefaultRoute(routes.length)]);
  };

  const removeRoute = (idx) => {
    const next = routes.filter((_, i) => i !== idx);
    updateRoutes(next.length ? next : [getDefaultRoute(0)]);
  };

  return (
    <div className="space-y-3">
      {routes.map((route, idx) => {
        const dataType = normalizeType(route.condition?.data_type);
        const allowedOperators = getAllowedOperators(dataType);
        const isUnary = UNARY_OPERATORS.has(route.condition?.operator);

        return (
          <div key={idx} className="rounded-md border border-border p-2 space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs text-muted-foreground">Route {idx + 1}</Label>
              <button
                type="button"
                onClick={() => removeRoute(idx)}
                className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
                title="Remove"
                disabled={routes.length <= 1}
              >
                ×
              </button>
            </div>

            <div className="prop-group">
              <Label className="text-xs font-medium">Route name</Label>
              <Input
                value={route.name}
                onChange={e => updateRoute(idx, { name: e.target.value })}
                placeholder={`Route ${idx + 1}`}
              />
            </div>

            <div className="prop-group">
              <Label className="text-xs font-medium">Variable to evaluate</Label>
              <Input
                placeholder="${VAR} / @{GLOBAL} / #{SECRET}"
                value={route.condition?.input || ''}
                onChange={e => updateRoute(idx, { condition: { input: e.target.value } })}
              />
            </div>

            <div className="prop-group">
              <Label className="text-xs font-medium">Data type</Label>
              <select
                value={dataType}
                onChange={e => {
                  const nextType = normalizeType(e.target.value);
                  const nextOps = getAllowedOperators(nextType);
                  updateRoute(idx, { condition: { data_type: nextType, operator: nextOps[0].value } });
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
                value={route.condition?.operator || allowedOperators[0].value}
                onChange={e => updateRoute(idx, { condition: { operator: e.target.value } })}
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
                  placeholder={dataType === 'object' ? 'property or ${VAR}/@{GLOBAL}/#{SECRET}' : 'literal or ${VAR}/@{GLOBAL}/#{SECRET}'}
                  value={route.condition?.compare_value || ''}
                  onChange={e => updateRoute(idx, { condition: { compare_value: e.target.value } })}
                />
              </div>
            )}
          </div>
        );
      })}

      <Button variant="outline" size="sm" className="w-full mt-1" onClick={addRoute}>
        + Add route
      </Button>

      <div className="rounded-md border border-border p-2">
        <p className="text-[11px] text-muted-foreground">
          Unmatched items are discarded (no default route).
        </p>
      </div>
    </div>
  );
}
