import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Button } from '@/components/ui/button';

export default function OpenaiResponsesNode({ data }) {
  const model = data.config?.model || 'gpt-5-mini';
  const out = data.config?.output_var || 'openai_response';
  const hasStructured = typeof data.config?.output_json_schema === 'string'
    ? data.config.output_json_schema.trim().length > 0
    : !!data.config?.output_json_schema;

  return (
    <BaseNode icon="🤖" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs space-y-1">
        <div className="font-semibold truncate max-w-[180px]">{model}</div>
        <div className="text-muted-foreground truncate max-w-[180px]">{out}</div>
        {hasStructured && <div className="text-[10px] text-emerald-600">structured output</div>}
      </div>
    </BaseNode>
  );
}

export function OpenaiResponsesPropsForm({ config, onChange }) {
  const includeFields = !!config.include_other_input_fields;
  const temperature = Number.isFinite(parseFloat(config.temperature))
    ? Math.min(2, Math.max(0, parseFloat(config.temperature)))
    : 0.7;
  const parseLegacyMessages = () => {
    if (Array.isArray(config.message)) return config.message;
    if (typeof config.message === 'string') {
      try {
        const parsed = JSON.parse(config.message);
        if (Array.isArray(parsed)) return parsed;
      } catch {
        // noop
      }
    }
    return [{ role: 'user', content: 'Hello' }];
  };

  const messages = parseLegacyMessages();

  const setMessage = (idx, field, value) => {
    const next = messages.map((m, i) => (i === idx ? { ...m, [field]: value } : m));
    onChange({ ...config, message: next });
  };

  const addMessage = () => {
    onChange({
      ...config,
      message: [...messages, { role: 'user', content: '' }],
    });
  };

  const removeMessage = (idx) => {
    const next = messages.filter((_, i) => i !== idx);
    onChange({
      ...config,
      message: next.length ? next : [{ role: 'user', content: '' }],
    });
  };

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label>Base URL</Label>
        <Input
          value={config.base_url || 'https://api.openai.com/v1'}
          placeholder="https://api.openai.com/v1"
          onChange={e => onChange({ ...config, base_url: e.target.value })}
        />
      </div>

      <div className="prop-group">
        <Label>API Key</Label>
        <Input
          type="password"
          autoComplete="off"
          value={config.api_key || ''}
          placeholder="#{OPENAI_API_KEY}"
          onChange={e => onChange({ ...config, api_key: e.target.value })}
        />
      </div>

      <div className="prop-group">
        <Label>Model</Label>
        <Input
          value={config.model || 'gpt-5-mini'}
          placeholder="gpt-5-mini"
          onChange={e => onChange({ ...config, model: e.target.value })}
        />
      </div>

      <div className="space-y-2">
        <Label>Messages</Label>
        {messages.map((msg, idx) => (
          <div key={idx} className="rounded-md border border-border p-2 space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-xs text-muted-foreground">Message {idx + 1}</Label>
              <button
                type="button"
                onClick={() => removeMessage(idx)}
                className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
                title="Remove"
              >
                ×
              </button>
            </div>
            <select
              value={String(msg.role || 'user').toLowerCase()}
              onChange={e => setMessage(idx, 'role', e.target.value)}
              className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
            >
              <option value="user">User</option>
              <option value="system">System</option>
            </select>
            <Input
              value={msg.content || ''}
              placeholder="Prompt"
              onChange={e => setMessage(idx, 'content', e.target.value)}
            />
          </div>
        ))}
        <Button variant="outline" size="sm" className="w-full" onClick={addMessage}>
          + Add message
        </Button>
        <p className="text-[11px] text-muted-foreground">
          Prompt supports <code>${'{'}VAR{'}'}</code> and <code>#{'{'}SECRET{'}'}</code> placeholders.
        </p>
      </div>

      <div className="prop-group">
        <Label>Instructions</Label>
        <Textarea
          value={config.instructions || 'You are a helpful assistant.'}
          onChange={e => onChange({ ...config, instructions: e.target.value })}
          className="text-xs min-h-[90px]"
        />
      </div>

      <div className="prop-group">
        <Label>Output JSON Schema (optional)</Label>
        <Textarea
          value={config.output_json_schema || ''}
          placeholder={'{\n  "type": "object",\n  "properties": {\n    "answer": {\n      "type": "string"\n    }\n  },\n  "additionalProperties": false,\n  "required": ["answer"]\n}'}
          onChange={e => onChange({ ...config, output_json_schema: e.target.value })}
          className="text-xs min-h-[140px] font-mono"
        />
        <p className="text-[11px] text-muted-foreground">
          Paste only the JSON Schema object. The node builds <code>text.format</code> automatically.
        </p>
      </div>

      <div className="prop-group">
        <Label>Temperature</Label>
        <Input
          type="number"
          min={0}
          max={2}
          step="0.1"
          value={temperature}
          onChange={e => {
            const parsed = parseFloat(e.target.value);
            const next = Number.isFinite(parsed) ? Math.min(2, Math.max(0, parsed)) : 0.7;
            onChange({ ...config, temperature: next });
          }}
        />
      </div>

      <div className="prop-group">
        <Label>Output variable</Label>
        <Input
          value={config.output_var || 'openai_response'}
          placeholder="openai_response"
          onChange={e => onChange({ ...config, output_var: e.target.value })}
        />
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Checkbox
          id="openai-responses-include-fields"
          checked={includeFields}
          onCheckedChange={(checked) => onChange({ ...config, include_other_input_fields: checked === true })}
        />
        <Label htmlFor="openai-responses-include-fields" className="text-sm text-muted-foreground cursor-pointer">
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
