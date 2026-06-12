import BaseNode from './BaseNode';
import { TimeDeltaFields } from './AddTimeToDateNode';

// ── Canvas card ────────────────────────────────────────────────────────
export default function SubtractTimeFromDateNode({ data }) {
  const { input_var, output_var } = data.config || {};
  return (
    <BaseNode icon="⏪" instanceName={data.instanceName} inputs={1} outputs={1}>
      <span className="font-mono text-xs">{input_var || '?'}</span>
      {' → '}
      <span className="font-mono text-xs">{output_var || 'new_date'}</span>
    </BaseNode>
  );
}

// ── Props form ─────────────────────────────────────────────────────────
export function SubtractTimeFromDatePropsForm({ config, onChange }) {
  return <TimeDeltaFields config={config} onChange={onChange} verb="subtract" />;
}
