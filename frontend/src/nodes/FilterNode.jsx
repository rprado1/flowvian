import { IfPropsForm } from './IfNode';
import { Handle, Position } from 'reactflow';

export default function FilterNode({ data }) {
  const conditions = Array.isArray(data.config?.conditions) ? data.config.conditions : [];

  return (
    <div style={{ minWidth: 220, position: 'relative' }}>
      <Handle type="target" position={Position.Left} id="input_1" />

      <div className="node-title-box">
        <span>🧹</span>
        <span>{data.instanceName || 'Filter'}</span>
      </div>

      <div className="node-body space-y-1">
        <div className="text-xs text-muted-foreground">Keep matching items</div>
        <div className="font-mono text-[11px] truncate">
          {conditions.length > 0 ? `${conditions.length} condition${conditions.length !== 1 ? 's' : ''}` : (data.config?.input || '${variable}')}
        </div>
      </div>

      <Handle type="source" position={Position.Right} id="output_1" />
    </div>
  );
}

export function FilterPropsForm(props) {
  return <IfPropsForm {...props} />;
}
