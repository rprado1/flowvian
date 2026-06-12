import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

// ── Canvas card ────────────────────────────────────────────────────────
export default function GetCurrentDateNode({ data }) {
  const varName = data.config?.output_var || 'current_date_utc';
  return (
    <BaseNode icon="📅" instanceName={data.instanceName} inputs={1} outputs={1}>
      → <span className="font-mono text-xs">{varName}</span>
    </BaseNode>
  );
}

// ── Props form ─────────────────────────────────────────────────────────
export function GetCurrentDatePropsForm({ config, onChange }) {
  return (
    <div className="prop-group">
      <Label>Output variable name</Label>
      <Input
        value={config.output_var ?? 'current_date_utc'}
        placeholder="current_date_utc"
        onChange={e => onChange({ ...config, output_var: e.target.value.trim() || 'current_date_utc' })}
      />
    </div>
  );
}
