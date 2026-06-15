import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';

export default function SplitNode({ data }) {
  const inputExpr = String(data.config?.input || '${items}');
  return (
    <BaseNode icon="✂️" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div className="font-semibold">Split array into items</div>
        <div className="font-mono text-[11px] truncate max-w-[190px]">{inputExpr}</div>
      </div>
    </BaseNode>
  );
}

export function SplitPropsForm({ config, onChange }) {
  const inputExpr = String(config.input || '${items}');
  const includeFields = !!config.include_other_input_fields;

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label className="text-xs font-medium">Variable to split</Label>
        <Input
          placeholder="${ARRAY_VAR}"
          value={inputExpr}
          onChange={(e) => onChange({ ...config, input: e.target.value })}
        />
        <p className="text-[11px] text-muted-foreground">
          Variable must resolve to an array for each input item.
        </p>
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Checkbox
          id="split-include-fields"
          checked={includeFields}
          onCheckedChange={(checked) => onChange({ ...config, include_other_input_fields: checked === true })}
        />
        <Label htmlFor="split-include-fields" className="text-sm text-muted-foreground cursor-pointer">
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
