import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from '@/components/ui/select';

// ── Canvas card ────────────────────────────────────────────────────────
export default function SchedulerNode({ data }) {
  const { config = {}, instanceName } = data;
  return (
    <BaseNode icon="⏱" instanceName={instanceName} inputs={0} outputs={1}>
      Every {config.interval ?? 60} {config.unit ?? 'seconds'}
    </BaseNode>
  );
}

// ── Props form (rendered in PropsPanel) ────────────────────────────────
export function SchedulerPropsForm({ config, onChange }) {
  return (
    <div className="space-y-4">
      <div className="prop-group">
        <Label>Interval</Label>
        <Input
          type="number"
          min={1}
          value={config.interval ?? 60}
          onChange={e => onChange({ ...config, interval: parseFloat(e.target.value) || 60 })}
        />
      </div>
      <div className="prop-group">
        <Label>Unit</Label>
        <Select
          value={config.unit ?? 'seconds'}
          onValueChange={v => onChange({ ...config, unit: v })}
        >
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="seconds">Seconds</SelectItem>
            <SelectItem value="minutes">Minutes</SelectItem>
            <SelectItem value="hours">Hours</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
