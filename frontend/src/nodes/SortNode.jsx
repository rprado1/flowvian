import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function SortNode({ data }) {
  const inputExpr = String(data.config?.input || '${value}');
  const order = String(data.config?.order || 'asc').toLowerCase() === 'desc' ? 'DESC' : 'ASC';

  return (
    <BaseNode icon="↕️" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div className="font-semibold">Sort list</div>
        <div className="font-mono text-[11px] truncate max-w-[190px]">{inputExpr}</div>
        <div className="text-[11px] text-muted-foreground">{order}</div>
      </div>
    </BaseNode>
  );
}

export function SortPropsForm({ config, onChange }) {
  const inputExpr = String(config.input || '${value}');
  const order = String(config.order || 'asc').toLowerCase() === 'desc' ? 'desc' : 'asc';

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label>Variable to sort</Label>
        <Input
          placeholder="${VARNAME}"
          value={inputExpr}
          onChange={e => onChange({ ...config, input: e.target.value })}
        />
        <p className="text-[11px] text-muted-foreground">
          Use an item variable placeholder like <code>${'{'}SCORE{'}'}</code>.
        </p>
      </div>

      <div className="prop-group">
        <Label>Order</Label>
        <select
          value={order}
          onChange={e => onChange({ ...config, order: e.target.value === 'desc' ? 'desc' : 'asc' })}
          className="w-full rounded-md border border-input bg-background px-2 py-2 text-sm"
        >
          <option value="asc">Ascending (ASC)</option>
          <option value="desc">Descending (DESC)</option>
        </select>
      </div>
    </div>
  );
}
