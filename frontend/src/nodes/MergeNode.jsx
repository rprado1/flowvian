import { useEffect } from 'react';
import { Handle, Position, useUpdateNodeInternals } from 'reactflow';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function MergeNode({ id, data }) {
  const updateNodeInternals = useUpdateNodeInternals();
  const branchCount = Math.max(2, parseInt(data.config?.branch_count ?? 2, 10) || 2);

  useEffect(() => {
    updateNodeInternals(id);
  }, [id, branchCount, updateNodeInternals]);

  const targetHandles = Array.from({ length: branchCount }, (_, idx) => {
    const top = ((idx + 1) / (branchCount + 1)) * 100;
    return (
      <Handle
        key={`in-${idx}`}
        type="target"
        position={Position.Left}
        id={`in-${idx}`}
        style={{ top: `${top}%` }}
      />
    );
  });

  return (
    <div style={{ minWidth: 200, minHeight: Math.max(110, 60 + branchCount * 18) }}>
      {targetHandles}
      <div className="node-title-box">
        <span>⬡</span>
        <span>{data.instanceName || 'Merge'}</span>
      </div>
      <div className="node-body">
        <span className="text-xs text-muted-foreground">
          Append {branchCount} branches
        </span>
      </div>
      <Handle type="source" position={Position.Right} id="out" />
    </div>
  );
}

export function MergePropsForm({ config, onChange }) {
  const branchCount = Math.max(2, parseInt(config.branch_count ?? 2, 10) || 2);

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label className="text-xs font-medium">Strategy</Label>
        <select
          value={config.strategy || 'append'}
          onChange={e => onChange({ ...config, strategy: e.target.value })}
          className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
        >
          <option value="append">Append</option>
        </select>
      </div>

      <div className="prop-group">
        <Label className="text-xs font-medium">Branches to combine</Label>
        <Input
          type="number"
          min={2}
          step={1}
          value={branchCount}
          onChange={e => {
            const parsed = parseInt(e.target.value, 10);
            const next = Number.isFinite(parsed) ? Math.max(2, parsed) : 2;
            onChange({ ...config, branch_count: next });
          }}
        />
      </div>
    </div>
  );
}
