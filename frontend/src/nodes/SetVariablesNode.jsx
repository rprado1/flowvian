import BaseNode from './BaseNode';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AlertTriangle } from 'lucide-react';

// ── Canvas card ────────────────────────────────────────────────────────
export default function SetVariablesNode({ data }) {
  const count = (data.config?.variables || []).length;
  const hasSecret = (data.config?.variables || []).some(v => String(v?.type || '').toLowerCase() === 'secret');
  return (
    <BaseNode icon="📦" instanceName={data.instanceName} inputs={1} outputs={1}>
      <div className="flex items-center gap-1">
        <span>{count} variable{count !== 1 ? 's' : ''}</span>
        {hasSecret ? (
          <TooltipProvider delayDuration={120}>
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex text-amber-500" aria-label="Secrets configured">
                  <AlertTriangle className="h-3.5 w-3.5" />
                </span>
              </TooltipTrigger>
              <TooltipContent className="max-w-[260px] text-xs leading-relaxed">
                Secret variables require env var <code>W_METADATA_1</code>. Example: <code>W_METADATA_1=&quot;&lt;MASTER_KEY_BASE64&gt;&quot;</code>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : null}
      </div>
    </BaseNode>
  );
}

// ── Props form ─────────────────────────────────────────────────────────
export function SetVariablesPropsForm({ config, onChange }) {
  const variables = config.variables || [];

  const normalizeType = (value) => {
    const t = String(value || 'string').toLowerCase();
    if (t === 'number' || t === 'boolean' || t === 'array' || t === 'object' || t === 'secret') return t;
    return 'string';
  };

  const getMode = (entry) => {
    if (normalizeType(entry?.type) === 'secret') return 'literal';
    return String(entry?.value_mode || (String(entry?.value || '').includes('${') ? 'template' : 'literal'));
  };

  const updateVar = (idx, field, value) => {
    const next = variables.map((v, i) => {
      if (i !== idx) return v;
      const updated = { ...v, [field]: value };
      const t = normalizeType(updated.type);
      if (field === 'type' && t === 'secret') {
        updated.value_mode = 'literal';
      }
      if (field === 'value_mode' && t === 'secret') {
        updated.value_mode = 'literal';
      }
      return updated;
    });
    onChange({ ...config, variables: next });
  };

  const addVar = () => {
    onChange({ ...config, variables: [...variables, { key: '', type: 'string', value_mode: 'literal', value: '' }] });
  };

  const removeVar = (idx) => {
    onChange({ ...config, variables: variables.filter((_, i) => i !== idx) });
  };

  const hasSecret = variables.some(v => normalizeType(v.type) === 'secret');

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Label>Variables</Label>
        {hasSecret ? (
          <TooltipProvider delayDuration={120}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="inline-flex items-center text-amber-500 hover:text-amber-400 transition-colors"
                  aria-label="Secret environment configuration"
                >
                  <AlertTriangle className="h-4 w-4" />
                </button>
              </TooltipTrigger>
              <TooltipContent className="max-w-[320px] text-xs leading-relaxed">
                Configure environment variable <code>W_METADATA_1</code> before run/build. Example: <code>W_METADATA_1=&quot;&lt;MASTER_KEY_BASE64&gt;&quot;</code>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ) : null}
      </div>
      {variables.map((v, idx) => (
        <div key={idx} className="rounded-md border border-border p-2 space-y-2">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">Variable {idx + 1}</Label>
            <button
              type="button"
              onClick={() => removeVar(idx)}
              className="text-muted-foreground hover:text-destructive transition-colors px-1 text-sm"
              title="Remove"
            >
              ×
            </button>
          </div>

          <Input
            placeholder="key"
            value={v.key}
            onChange={e => updateVar(idx, 'key', e.target.value)}
          />

          <select
            value={normalizeType(v.type)}
            onChange={e => updateVar(idx, 'type', e.target.value)}
            className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
          >
            <option value="string">String</option>
            <option value="number">Number</option>
            <option value="boolean">Boolean</option>
            <option value="array">Array</option>
            <option value="object">Object</option>
            <option value="secret">Secret</option>
          </select>

          <select
            value={getMode(v)}
            onChange={e => updateVar(idx, 'value_mode', e.target.value)}
            className="w-full rounded-md border border-input bg-background px-2 py-1 text-xs"
            disabled={normalizeType(v.type) === 'secret'}
          >
            <option value="literal">Literal</option>
            <option value="template">Template (${`{var}`})</option>
            <option value="path">Path (input object)</option>
          </select>

          <Input
            type={normalizeType(v.type) === 'secret' ? 'password' : 'text'}
            placeholder={
              normalizeType(v.type) === 'secret'
                ? 'Secret value'
                : getMode(v) === 'path'
                ? 'args.country or items[0].id'
                : normalizeType(v.type) === 'array'
                  ? '["a",1,true] or ${items}'
                  : normalizeType(v.type) === 'object'
                    ? '{"k":"v"} or ${obj}'
                    : 'value or ${variable}'
            }
            value={v.value || ''}
            onChange={e => updateVar(idx, 'value', e.target.value)}
            autoComplete="off"
          />

          <p className="text-[11px] text-muted-foreground">
            {normalizeType(v.type) === 'secret'
              ? 'Stored encrypted. Configure W_METADATA_1 to decrypt at runtime.'
              : getMode(v) === 'path'
              ? 'Use path notation like args.country or items[0].id.'
              : 'Use '} 
            {normalizeType(v.type) === 'secret'
              ? null
              : getMode(v) === 'path'
              ? null
              : <code>${'{'}variable{'}'}</code>} 
            {normalizeType(v.type) === 'secret'
              ? null
              : getMode(v) === 'path'
              ? null
              : ' to reference flow input values.'}
          </p>
        </div>
      ))}
      <Button variant="outline" size="sm" className="w-full mt-1" onClick={addVar}>
        + Add variable
      </Button>
      
      <div className="flex items-center gap-2 pt-2">
        <Checkbox
          id="include-input-fields-sv"
          checked={config.include_other_input_fields || false}
          onCheckedChange={(checked) =>
            onChange({ ...config, include_other_input_fields: checked })
          }
        />
        <Label
          htmlFor="include-input-fields-sv"
          className="text-sm text-muted-foreground cursor-pointer"
        >
          Include Other Input Fields
        </Label>
      </div>
    </div>
  );
}
