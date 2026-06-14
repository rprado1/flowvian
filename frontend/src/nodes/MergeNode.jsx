import { Handle, Position } from 'reactflow';
import { Label } from '@/components/ui/label';

export default function MergeNode({ data }) {
  return (
    <div style={{ minWidth: 200 }}>
      <Handle type="target" position={Position.Left} id="in-0" style={{ top: '30%' }} />
      <Handle type="target" position={Position.Left} id="in-1" style={{ top: '70%' }} />
      <div className="node-title-box">
        <span>⬡</span>
        <span>{data.instanceName || 'Merge'}</span>
      </div>
      <div className="node-body">
        <span className="text-xs text-muted-foreground">Append branches</span>
      </div>
      <Handle type="source" position={Position.Right} id="out" />
    </div>
  );
}

export function MergePropsForm({ config, onChange }) {
  return (
    <div className="space-y-2">
      <Label className="text-xs font-medium">Strategy</Label>
      <select
        value={config.strategy || 'append'}
        onChange={e => onChange({ ...config, strategy: e.target.value })}
        className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
      >
        <option value="append">Append</option>
      </select>
    </div>
  );
}
