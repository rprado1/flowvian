import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function WaitNode({ data }) {
  const seconds = Number.isFinite(parseFloat(data.config?.seconds))
    ? Math.max(0, parseFloat(data.config.seconds))
    : 1;
  return (
    <BaseNode icon="⏳" instanceName={data.instanceName} inputs={1} outputs={1}>
      Wait {seconds}s
    </BaseNode>
  );
}

export function WaitPropsForm({ config, onChange }) {
  const seconds = Number.isFinite(parseFloat(config.seconds))
    ? Math.max(0, parseFloat(config.seconds))
    : 1;

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label className="text-xs font-medium">Seconds</Label>
        <Input
          type="number"
          min={0}
          step="any"
          value={seconds}
          onChange={e => {
            const parsed = parseFloat(e.target.value);
            const next = Number.isFinite(parsed) ? Math.max(0, parsed) : 1;
            onChange({ ...config, seconds: next });
          }}
        />
      </div>
    </div>
  );
}
