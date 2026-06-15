import BaseNode from './BaseNode';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

export default function StopAndErrorNode({ data }) {
  const message = (data.config?.message || 'Execution stopped by business rule').trim();
  return (
    <BaseNode icon="⛔" instanceName={data.instanceName} inputs={1} outputs={0}>
      <div className="text-xs">
        <div className="font-semibold">Stop current execution</div>
        <div className="text-muted-foreground truncate max-w-[180px]">{message}</div>
      </div>
    </BaseNode>
  );
}

export function StopAndErrorPropsForm({ config, onChange }) {
  const message = typeof config.message === 'string'
    ? config.message
    : 'Execution stopped by business rule';

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label className="text-xs font-medium">Message</Label>
        <Textarea
          value={message}
          onChange={(e) => onChange({ ...config, message: e.target.value })}
          className="text-xs min-h-[90px]"
          placeholder="Execution stopped by business rule"
        />
        <p className="text-xs text-muted-foreground mt-1">You can use ${'{VARIABLE}'}</p>
      </div>
    </div>
  );
}
