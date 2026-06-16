import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

export default function AggregateNode({ data }) {
  const outputVar = String(data.config?.output_var || 'items');

  return (
    <BaseNode icon="🧺" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div className="font-semibold">Aggregate all items</div>
        <div className="font-mono text-[11px] truncate max-w-[190px]">{outputVar}</div>
      </div>
    </BaseNode>
  );
}

export function AggregatePropsForm({ config, onChange }) {
  const outputVar = String(config.output_var || 'items');
  const includeFields = !!config.include_other_input_fields;

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label className="text-xs font-medium">Output variable</Label>
        <Input
          placeholder="items"
          value={outputVar}
          onChange={(e) => onChange({ ...config, output_var: e.target.value })}
        />
        <p className="text-[11px] text-muted-foreground">
          This field will contain the aggregated list of all input items.
        </p>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Checkbox
          id="aggregate-include-fields"
          checked={includeFields}
          onCheckedChange={(checked) => onChange({ ...config, include_other_input_fields: checked === true })}
        />
        <Label htmlFor="aggregate-include-fields" className="text-sm text-muted-foreground cursor-pointer">
          Include Other Input Fields (from first item)
        </Label>
      </div>
    </div>
  );
}
