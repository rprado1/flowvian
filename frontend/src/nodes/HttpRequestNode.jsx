import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';

export default function HttpRequestNode({ data }) {
  const method = (data.config?.method || 'GET').toUpperCase();
  const url = data.config?.url || 'https://api.example.com';
  return (
    <BaseNode icon="🌐" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="text-xs">
        <div className="font-semibold">{method}</div>
        <div className="text-muted-foreground truncate max-w-[160px]">{url}</div>
      </div>
    </BaseNode>
  );
}

export function HttpRequestPropsForm({ config, onChange }) {
  const method = (config.method || 'GET').toUpperCase();
  const headers = Array.isArray(config.headers) ? config.headers : [];
  const queryParams = Array.isArray(config.query_params) ? config.query_params : [];

  const setHeader = (idx, field, value) => {
    const next = headers.map((h, i) => (i === idx ? { ...h, [field]: value } : h));
    onChange({ ...config, headers: next });
  };

  const addHeader = () => {
    onChange({ ...config, headers: [...headers, { key: '', value: '' }] });
  };

  const removeHeader = (idx) => {
    onChange({ ...config, headers: headers.filter((_, i) => i !== idx) });
  };

  const setQueryParam = (idx, field, value) => {
    const next = queryParams.map((p, i) => (i === idx ? { ...p, [field]: value } : p));
    onChange({ ...config, query_params: next });
  };

  const addQueryParam = () => {
    onChange({ ...config, query_params: [...queryParams, { key: '', value: '' }] });
  };

  const removeQueryParam = (idx) => {
    onChange({ ...config, query_params: queryParams.filter((_, i) => i !== idx) });
  };

  const timeoutSeconds = Number.isFinite(parseFloat(config.timeout_seconds))
    ? Math.min(120, Math.max(1, parseFloat(config.timeout_seconds)))
    : 30;

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
        </select>
      </div>

      <div className="prop-group">
        <Label className="text-xs font-medium">URL</Label>
        <Input
          value={config.url || ''}
          placeholder="https://api.example.com/users"
          onChange={e => onChange({ ...config, url: e.target.value })}
        />
        {method === 'GET' && (
          <p className="text-xs text-muted-foreground mt-1">
            For GET, define query string in Query Params section.
          </p>
        )}
      </div>

      {method === 'GET' && (
        <div className="space-y-2">
          <Label className="text-xs font-medium">Query Params</Label>
          {queryParams.map((p, idx) => (
            <div key={idx} className="var-row">
              <Input
                placeholder="Param name"
                value={p.key || ''}
                onChange={e => setQueryParam(idx, 'key', e.target.value)}
              />
              <Input
                placeholder="Param value"
                value={p.value || ''}
                onChange={e => setQueryParam(idx, 'value', e.target.value)}
              />
              <button
                type="button"
                onClick={() => removeQueryParam(idx)}
                className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
                title="Remove"
              >
                ×
              </button>
            </div>
          ))}
          <Button variant="outline" size="sm" className="w-full" onClick={addQueryParam}>
            + Add query param
          </Button>
        </div>
      )}

      <div className="prop-group">
        <Label className="text-xs font-medium">Timeout (seconds)</Label>
        <Input
          type="number"
          min={1}
          max={120}
          step="any"
          value={timeoutSeconds}
          onChange={e => {
            const parsed = parseFloat(e.target.value);
            const next = Number.isFinite(parsed) ? Math.min(120, Math.max(1, parsed)) : 30;
            onChange({ ...config, timeout_seconds: next });
          }}
        />
      </div>

      <div className="space-y-2">
        <Label className="text-xs font-medium">Headers</Label>
        {headers.map((h, idx) => (
          <div key={idx} className="var-row">
            <Input
              placeholder="Header name"
              value={h.key || ''}
              onChange={e => setHeader(idx, 'key', e.target.value)}
            />
            <Input
              placeholder="Header value"
              value={h.value || ''}
              onChange={e => setHeader(idx, 'value', e.target.value)}
            />
            <button
              type="button"
              onClick={() => removeHeader(idx)}
              className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
              title="Remove"
            >
              ×
            </button>
          </div>
        ))}
        <Button variant="outline" size="sm" className="w-full" onClick={addHeader}>
          + Add header
        </Button>
      </div>

      {method === 'POST' && (
        <div className="prop-group">
          <Label className="text-xs font-medium">Body Raw JSON</Label>
          <Textarea
            value={config.body_raw_json || '{\n  "key": "${VALUE}"\n}'}
            onChange={e => onChange({ ...config, body_raw_json: e.target.value })}
            className="font-mono text-xs min-h-[120px]"
          />
        </div>
      )}

      <div className="flex items-center gap-2 pt-2">
        <Checkbox
          id="include-input-fields-http"
          checked={config.include_other_input_fields || false}
          onCheckedChange={(checked) =>
            onChange({ ...config, include_other_input_fields: checked })
          }
        />
        <Label
          htmlFor="include-input-fields-http"
          className="text-sm text-muted-foreground cursor-pointer"
        >
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
