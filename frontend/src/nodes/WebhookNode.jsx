import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';

export default function WebhookNode({ data }) {
  const config = data.config || {};
  const method = (config.method || 'POST').toUpperCase();
  const host = config.host || '0.0.0.0';
  const port = config.port || 8000;
  const path = config.path || '/webhook';

  return (
    <BaseNode icon="🪝" instanceName={data.instanceName} inputs={0} outputs={1}>
      <div className="text-xs">
        <div className="font-semibold">{method} {path}</div>
        <div className="text-muted-foreground truncate max-w-[170px]">{host}:{port}</div>
      </div>
    </BaseNode>
  );
}

export function WebhookPropsForm({ config, onChange }) {
  const method = (config.method || 'POST').toUpperCase();
  const inputParams = Array.isArray(config.input_params) ? config.input_params : [];

  const setInputParam = (idx, field, value) => {
    const next = inputParams.map((param, i) => (i === idx ? { ...param, [field]: value } : param));
    onChange({ ...config, input_params: next });
  };

  const addInputParam = () => {
    onChange({
      ...config,
      input_params: [
        ...inputParams,
        { name: '', type: 'string', source: 'query', required: false },
      ],
    });
  };

  const removeInputParam = (idx) => {
    onChange({
      ...config,
      input_params: inputParams.filter((_, i) => i !== idx),
    });
  };

  return (
    <div className="space-y-3">
      <div className="prop-group">
        <Label className="text-xs font-medium">Method</Label>
        <select
          value={method}
          onChange={e => onChange({ ...config, method: e.target.value })}
          className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
        >
          <option value="GET">GET</option>
          <option value="POST">POST</option>
          <option value="BOTH">BOTH</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="prop-group">
          <Label className="text-xs font-medium">Host</Label>
          <Input
            value={config.host || '0.0.0.0'}
            onChange={e => onChange({ ...config, host: e.target.value })}
            placeholder="0.0.0.0"
          />
        </div>
        <div className="prop-group">
          <Label className="text-xs font-medium">Port</Label>
          <Input
            type="number"
            min={1}
            max={65535}
            value={config.port ?? 8000}
            onChange={e => onChange({ ...config, port: parseInt(e.target.value || '8000', 10) || 8000 })}
          />
        </div>
      </div>

      <div className="prop-group">
        <Label className="text-xs font-medium">Path</Label>
        <Input
          value={config.path || '/webhook'}
          onChange={e => onChange({ ...config, path: e.target.value })}
          placeholder="/webhook"
        />
      </div>

      <div className="space-y-2">
        <Label className="text-xs font-medium">Input Params</Label>
        {inputParams.map((param, idx) => (
          <div key={idx} className="space-y-2 rounded-md border border-border p-2">
            <Input
              placeholder="Param name"
              value={param.name || ''}
              onChange={e => setInputParam(idx, 'name', e.target.value)}
            />
            <div className="grid grid-cols-2 gap-2">
              <select
                value={param.type || 'string'}
                onChange={e => setInputParam(idx, 'type', e.target.value)}
                className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
              >
                <option value="string">string</option>
                <option value="number">number</option>
                <option value="boolean">boolean</option>
                <option value="object">object</option>
                <option value="array">array</option>
              </select>
              <select
                value={param.source || 'query'}
                onChange={e => setInputParam(idx, 'source', e.target.value)}
                className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
              >
                <option value="query">query</option>
                <option value="body">body</option>
                <option value="header">header</option>
              </select>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Checkbox
                  id={`webhook-required-${idx}`}
                  checked={param.required || false}
                  onCheckedChange={(checked) => setInputParam(idx, 'required', !!checked)}
                />
                <Label htmlFor={`webhook-required-${idx}`} className="text-xs">Required</Label>
              </div>
              <button
                type="button"
                onClick={() => removeInputParam(idx)}
                className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
                title="Remove"
              >
                ×
              </button>
            </div>
          </div>
        ))}
        <Button variant="outline" size="sm" className="w-full" onClick={addInputParam}>
          + Add input param
        </Button>
      </div>

      <div className="space-y-2 rounded-md border border-border p-2">
        <p className="text-xs font-medium">Response Mapping (from workflow output)</p>
        <Input
          value={config.response_body_var || 'webhook_response_body'}
          onChange={e => onChange({ ...config, response_body_var: e.target.value })}
          placeholder="response body var"
        />
        <Input
          value={config.response_status_var || 'webhook_status_code'}
          onChange={e => onChange({ ...config, response_status_var: e.target.value })}
          placeholder="status code var"
        />
        <Input
          value={config.response_headers_var || 'webhook_headers'}
          onChange={e => onChange({ ...config, response_headers_var: e.target.value })}
          placeholder="headers object var"
        />
        <p className="text-[11px] text-muted-foreground">
          The workflow should set these variables in terminal items.
        </p>
      </div>
    </div>
  );
}
