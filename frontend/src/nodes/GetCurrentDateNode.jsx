import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

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
    <div className="space-y-3">
      <div className="prop-group">
        <Label>Output variable name</Label>
        <Input
          value={config.output_var ?? 'current_date_utc'}
          placeholder="current_date_utc"
          onChange={e => onChange({ ...config, output_var: e.target.value.trim() || 'current_date_utc' })}
        />
      </div>
      
      <div className="flex items-center gap-2 pt-2">
        <Checkbox
          id="include-input-fields"
          checked={config.include_other_input_fields || false}
          onCheckedChange={(checked) =>
            onChange({ ...config, include_other_input_fields: checked })
          }
        />
        <Label
          htmlFor="include-input-fields"
          className="text-sm text-muted-foreground cursor-pointer"
        >
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
