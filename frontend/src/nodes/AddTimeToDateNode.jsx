import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

// ── Canvas card ────────────────────────────────────────────────────────
export default function AddTimeToDateNode({ data }) {
  const { input_var, output_var } = data.config || {};
  return (
    <BaseNode icon="⏩" instanceName={data.instanceName} inputs={1} outputs={1}>
      <span className="font-mono text-xs">{input_var || '?'}</span>
      {' → '}
      <span className="font-mono text-xs">{output_var || 'new_date'}</span>
    </BaseNode>
  );
}

// ── Shared timedelta form fields ───────────────────────────────────────
export function TimeDeltaFields({ config, onChange, verb = 'add' }) {
  const fields = ['days', 'hours', 'minutes', 'seconds'];
  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label>Input datetime variable</Label>
        <Input
          value={config.input_var ?? ''}
          placeholder="variable name"
          onChange={e => onChange({ ...config, input_var: e.target.value.trim() })}
        />
      </div>
      {fields.map(f => (
        <div key={f} className="prop-group">
          <Label>{f.charAt(0).toUpperCase() + f.slice(1)} to {verb}</Label>
          <Input
            type="number"
            min={0}
            value={config[f] ?? 0}
            onChange={e => onChange({ ...config, [f]: parseFloat(e.target.value) || 0 })}
          />
        </div>
      ))}
      <div className="prop-group">
        <Label>Output variable name</Label>
        <Input
          value={config.output_var ?? 'new_date'}
          placeholder="new_date"
          onChange={e => onChange({ ...config, output_var: e.target.value.trim() || 'new_date' })}
        />
      </div>
      
      <div className="flex items-center gap-2 pt-2">
        <Checkbox
          id={`include-input-fields-${verb}`}
          checked={config.include_other_input_fields || false}
          onCheckedChange={(checked) =>
            onChange({ ...config, include_other_input_fields: checked })
          }
        />
        <Label
          htmlFor={`include-input-fields-${verb}`}
          className="text-sm text-muted-foreground cursor-pointer"
        >
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}

// ── Props form ─────────────────────────────────────────────────────────
export function AddTimeToDatePropsForm({ config, onChange }) {
  return <TimeDeltaFields config={config} onChange={onChange} verb="add" />;
}
