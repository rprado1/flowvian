import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

const FORMAT_OPTIONS = [
  { value: 'iso_8601', label: 'ISO 8601' },
  { value: 'date_yyyy_mm_dd', label: 'YYYY-MM-DD' },
  { value: 'datetime_yyyy_mm_dd_hh_mm_ss', label: 'YYYY-MM-DD HH:mm:ss' },
  { value: 'time_hh_mm_ss', label: 'HH:mm:ss' },
  { value: 'unix_timestamp', label: 'Unix Timestamp (s)' },
  { value: 'unix_ms_timestamp', label: 'Unix Ms Timestamp' },
];

export default function FormatDateNode({ data }) {
  const inputExpr = String(data.config?.input || '${current_date_utc}');
  const formatName = String(data.config?.format || 'iso_8601');
  const outputVar = String(data.config?.output_var || 'formatted_date');

  const option = FORMAT_OPTIONS.find(opt => opt.value === formatName);
  const formatLabel = option ? option.label : formatName;

  return (
    <BaseNode icon="🗓️" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div className="font-mono text-[11px] truncate max-w-[190px]">{inputExpr}</div>
        <div className="text-muted-foreground truncate max-w-[190px]">{formatLabel}</div>
        <div className="font-mono text-[11px] truncate max-w-[190px]">{outputVar}</div>
      </div>
    </BaseNode>
  );
}

export function FormatDatePropsForm({ config, onChange }) {
  const inputExpr = String(config.input || '${current_date_utc}');
  const outputVar = String(config.output_var || 'formatted_date');
  const formatName = String(config.format || 'iso_8601');
  const includeFields = !!config.include_other_input_fields;

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label>Input variable</Label>
        <Input
          placeholder="${VARIABLE} or @{GLOBAL_VAR}"
          value={inputExpr}
          onChange={e => onChange({ ...config, input: e.target.value })}
        />
      </div>

      <div className="prop-group">
        <Label>Output format</Label>
        <select
          value={formatName}
          onChange={e => onChange({ ...config, format: e.target.value })}
          className="w-full rounded-md border border-input bg-background px-2 py-2 text-sm"
        >
          {FORMAT_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div className="prop-group">
        <Label>Output variable name</Label>
        <Input
          placeholder="formatted_date"
          value={outputVar}
          onChange={e => onChange({ ...config, output_var: e.target.value })}
        />
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Checkbox
          id="format-date-include-fields"
          checked={includeFields}
          onCheckedChange={(checked) => onChange({ ...config, include_other_input_fields: checked === true })}
        />
        <Label htmlFor="format-date-include-fields" className="text-sm text-muted-foreground cursor-pointer">
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
