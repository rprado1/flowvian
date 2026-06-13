import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';

// ── Canvas card ────────────────────────────────────────────────────────
export default function SetVariablesNode({ data }) {
  const count = (data.config?.variables || []).length;
  return (
    <BaseNode icon="📦" instanceName={data.instanceName} inputs={1} outputs={1}>
      {count} variable{count !== 1 ? 's' : ''}
    </BaseNode>
  );
}

// ── Props form ─────────────────────────────────────────────────────────
export function SetVariablesPropsForm({ config, onChange }) {
  const variables = config.variables || [];

  const updateVar = (idx, field, value) => {
    const next = variables.map((v, i) => i === idx ? { ...v, [field]: value } : v);
    onChange({ ...config, variables: next });
  };

  const addVar = () => {
    onChange({ ...config, variables: [...variables, { key: '', value: '' }] });
  };

  const removeVar = (idx) => {
    onChange({ ...config, variables: variables.filter((_, i) => i !== idx) });
  };

  return (
    <div className="space-y-3">
      <Label>Variables</Label>
      {variables.map((v, idx) => (
        <div key={idx} className="var-row">
          <Input
            placeholder="key"
            value={v.key}
            onChange={e => updateVar(idx, 'key', e.target.value)}
          />
          <Input
            placeholder="value"
            value={v.value}
            onChange={e => updateVar(idx, 'value', e.target.value)}
          />
          <button
            type="button"
            onClick={() => removeVar(idx)}
            className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
            title="Remove"
          >
            ×
          </button>
        </div>
      ))}
      <Button variant="outline" size="sm" className="w-full mt-1" onClick={addVar}>
        + Add variable
      </Button>
      
      <div className="flex items-center gap-2 pt-2">
        <Checkbox
          id="include-input-fields-sv"
          checked={config.include_other_input_fields || false}
          onCheckedChange={(checked) =>
            onChange({ ...config, include_other_input_fields: checked })
          }
        />
        <Label
          htmlFor="include-input-fields-sv"
          className="text-sm text-muted-foreground cursor-pointer"
        >
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
