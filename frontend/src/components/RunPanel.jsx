import { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

function valueToText(value) {
  if (value == null) return '';
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch (error) {
      void error;
      return '[unserializable object]';
    }
  }
  return String(value);
}

function shouldTruncateValue(value) {
  return typeof value !== 'object' || value == null;
}

function fmtItems(items) {
  if (!items || !Array.isArray(items) || !items.length) {
    return <span className="text-muted-foreground">—</span>;
  }
  
  return (
    <span className="block break-all whitespace-normal">
      <span className="text-muted-foreground text-xs">
        {items.length} item{items.length !== 1 ? 's' : ''}
      </span>
      {items.map((item, idx) => {
        const entries = Object.entries(item);
        return (
          <span key={idx} className="block text-xs mt-1 pl-2 border-l-2 border-border">
            {entries.map(([k, v]) => {
              let val = valueToText(v);
              if (shouldTruncateValue(v) && val.length > 40) val = val.substring(0, 37) + '…';
              return (
                <span key={k} className="block">
                  <code className="run-ctx">{k}</code> = {val}
                </span>
              );
            })}
          </span>
        );
      })}
    </span>
  );
}

function fmtIfEvaluations(debug) {
  const evaluations = Array.isArray(debug?.if_evaluations) ? debug.if_evaluations : [];
  if (!evaluations.length) return null;

  return (
    <div className="mt-2 space-y-2">
      {evaluations.slice(0, 10).map((ev, idx) => {
        const conditions = Array.isArray(ev.conditions) ? ev.conditions : [];
        return (
          <div key={idx} className="rounded border border-border p-2 bg-muted/30">
            <div className="text-[11px] font-semibold mb-1">
              Item #{idx + 1} - Final: {ev.final_result ? 'True' : 'False'}
            </div>
            {conditions.map((c, cidx) => (
              <div key={cidx} className="text-[11px] leading-5">
                {cidx > 0 && c.join && (
                  <span className="font-semibold mr-1">{c.join}</span>
                )}
                <code className="run-ctx">{c.variable || '${?}'}</code>
                <span> ({String(c.resolved_value)}) </span>
                <span>{c.operator} </span>
                {c.compare_value != null && (
                  <>
                    <span>{String(c.compare_value)} </span>
                    <span className="text-muted-foreground">[{String(c.resolved_compare)}]</span>
                  </>
                )}
                <span> - </span>
                <span className={c.result ? 'text-emerald-600' : 'text-rose-600'}>{c.result ? 'True' : 'False'}</span>
              </div>
            ))}
          </div>
        );
      })}
      {evaluations.length > 10 && (
        <div className="text-[11px] text-muted-foreground">+{evaluations.length - 10} more evaluated items</div>
      )}
    </div>
  );
}

function fmtHttpRequestDetails(trace) {
  if (!trace || trace.type !== 'http_request') return null;

  const itemsOut = Array.isArray(trace.items_out) ? trace.items_out : [];
  if (!itemsOut.length) return null;

  const sample = itemsOut.find(item => item && typeof item === 'object') || null;
  if (!sample) return null;

  const method = String(sample.http_method || '').toUpperCase();
  const params = sample.http_request_params;
  const bodyJson = sample.http_request_body_json;

  if (method === 'GET' && (params == null || (typeof params === 'object' && Object.keys(params).length === 0))) {
    return null;
  }
  if (method === 'POST' && (bodyJson == null || String(bodyJson).trim() === '')) {
    return null;
  }

  return (
    <div className="mt-2 rounded border border-border p-2 bg-muted/30 text-[11px] space-y-1">
      <div className="font-semibold">HTTP Request Sent</div>
      {method === 'GET' && params != null && (
        <div>
          <span className="text-muted-foreground">Params: </span>
          <code className="run-ctx">{valueToText(params)}</code>
        </div>
      )}
      {method === 'POST' && bodyJson != null && (
        <div>
          <span className="text-muted-foreground">Body JSON: </span>
          <code className="run-ctx">{String(bodyJson)}</code>
        </div>
      )}
    </div>
  );
}

function toEpochSeconds(value) {
  if (typeof value === 'number' && !Number.isNaN(value)) return value;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const numeric = Number(trimmed);
    if (!Number.isNaN(numeric)) return numeric;
    const parsedMs = Date.parse(trimmed);
    if (!Number.isNaN(parsedMs)) return parsedMs / 1000;
  }
  return null;
}

function formatTraceTime(ts) {
  if (typeof ts !== 'number' || Number.isNaN(ts)) return '—';
  return new Date(ts * 1000).toLocaleString('en-US');
}

function resolveTraceTimes(trace) {
  const fallbackTs =
    toEpochSeconds(trace?.ts)
    ?? toEpochSeconds(trace?.timestamp)
    ?? toEpochSeconds(trace?.time)
    ?? null;

  const startTs =
    toEpochSeconds(trace?.start_ts)
    ?? toEpochSeconds(trace?.started_at)
    ?? toEpochSeconds(trace?.start)
    ?? fallbackTs;

  const endTs =
    toEpochSeconds(trace?.end_ts)
    ?? toEpochSeconds(trace?.finished_at)
    ?? toEpochSeconds(trace?.end)
    ?? fallbackTs;

  return { startTs, endTs };
}

export default function RunPanel({ traces, output, finalOutput, onClose }) {
  const [copiedKey, setCopiedKey] = useState('');

  const setCopiedFeedback = (key) => {
    setCopiedKey(key);
    window.setTimeout(() => {
      setCopiedKey((prev) => (prev === key ? '' : prev));
    }, 1500);
  };

  const copyToClipboard = async (text, key) => {
    const value = String(text ?? '');
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
        setCopiedFeedback(key);
        return;
      }
    } catch (error) {
      void error;
    }

    const area = document.createElement('textarea');
    area.value = value;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.left = '-9999px';
    document.body.appendChild(area);
    area.select();
    document.execCommand('copy');
    document.body.removeChild(area);
    setCopiedFeedback(key);
  };

  const outputAsText = typeof output === 'string' ? output : JSON.stringify(output ?? null, null, 2);
  const finalOutputAsText = JSON.stringify(finalOutput ?? null, null, 2);

  const renderFinalOutput = (finalOutput) => {
    if (finalOutput && finalOutput.status === 'stopped_current_execution') {
      return (
        <div className="mx-4 mt-2 rounded-md border border-amber-500/40 bg-amber-500/5 p-2 text-xs">
          <div className="font-semibold text-amber-700">Execution stopped (current run)</div>
          <div className="text-muted-foreground mt-1">
            {finalOutput.stop_reason || 'Execution stopped by Stop and Error node'}
          </div>
        </div>
      );
    }

    if (!finalOutput || !finalOutput.branches || typeof finalOutput.branches !== 'object') {
      return null;
    }

    const entries = Object.entries(finalOutput.branches);
    const branchElapsed = (finalOutput && typeof finalOutput.branch_elapsed_seconds === 'object' && finalOutput.branch_elapsed_seconds)
      ? finalOutput.branch_elapsed_seconds
      : {};
    if (!entries.length) {
      return (
        <div className="mx-4 mt-2 rounded-md border border-border p-2 text-xs text-muted-foreground">
          Final Output: no terminal branches
        </div>
      );
    }

    return (
      <div className="mx-4 mt-2 rounded-md border border-border p-2">
        <div className="mb-2 flex items-center justify-between gap-2">
          <div className="text-xs font-semibold">Final Output (by terminal branch)</div>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-6 px-2 text-[11px]"
            onClick={() => copyToClipboard(finalOutputAsText, 'final-output')}
          >
            {copiedKey === 'final-output' ? 'Copied' : 'Copy JSON'}
          </Button>
        </div>
        {entries.map(([branchId, items]) => (
          <div key={branchId} className="mb-2 last:mb-0">
            <div className="text-xs text-muted-foreground mb-1 flex items-center gap-2">
              <code className="run-ctx">{branchId}</code>
              {Object.prototype.hasOwnProperty.call(branchElapsed, branchId) && (
                <span>
                  ({branchElapsed[branchId] == null ? 'n/a' : `${branchElapsed[branchId]}s`})
                </span>
              )}
            </div>
            <div className="text-xs">{fmtItems(items)}</div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div id="run-panel" className="flex flex-col" style={{ height: 240, flexShrink: 0 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-border" style={{ background: 'hsl(var(--card))' }}>
        <span className="text-sm font-semibold">Run Results</span>
        <Button variant="ghost" size="sm" onClick={onClose} className="h-6 px-2 text-xs">
          ✕ Close
        </Button>
      </div>

      <ScrollArea className="flex-1">
        {output && (
          <div className="mx-4 mt-2">
            <div className="mb-1 flex items-center justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-6 px-2 text-[11px]"
                onClick={() => copyToClipboard(outputAsText, 'run-output')}
              >
                {copiedKey === 'run-output' ? 'Copied' : 'Copy JSON'}
              </Button>
            </div>
            <pre className="build-log-pre text-xs" style={{ maxHeight: 80 }}>{outputAsText}</pre>
          </div>
        )}
        {renderFinalOutput(finalOutput)}
        <Table className="table-fixed w-full">
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="w-8 text-muted-foreground">#</TableHead>
              <TableHead className="w-40 text-muted-foreground">Node</TableHead>
              <TableHead className="w-24 text-muted-foreground">Type</TableHead>
              <TableHead className="w-36 text-muted-foreground">Time</TableHead>
              <TableHead className="w-24 text-muted-foreground">Status</TableHead>
              <TableHead className="w-[30%] text-muted-foreground">Items In</TableHead>
              <TableHead className="w-[30%] text-muted-foreground">Items Out</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {traces.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-4">
                  No nodes executed
                </TableCell>
              </TableRow>
            )}
            {traces.map((tr, i) => {
              const isStopped = tr.status === 'stopped_current_execution';
              const rowClass = isStopped ? 'run-ok' : (tr.status !== 'ok' ? 'run-err' : 'run-ok');
              const { startTs, endTs } = resolveTraceTimes(tr);
              return (
              <TableRow key={i} className={`border-border ${rowClass}`}>
                <TableCell className="text-xs">{i + 1}</TableCell>
                <TableCell className="text-xs font-semibold break-words">{tr.label || tr.id || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground break-words">{tr.type || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground break-words">
                  <span className="block">Start: {formatTraceTime(startTs)}</span>
                  <span className="block">End: {formatTraceTime(endTs)}</span>
                </TableCell>
                <TableCell className="text-xs break-words">
                  {tr.status === 'ok' ? '✅' : (isStopped ? '🛑' : '❌')} {tr.status}
                </TableCell>
                <TableCell className="text-xs align-top max-w-[420px] break-all whitespace-normal">{fmtItems(tr.items_in)}</TableCell>
                <TableCell className="text-xs align-top max-w-[420px] break-all whitespace-normal">
                  {fmtItems(tr.items_out)}
                  {fmtHttpRequestDetails(tr)}
                  {tr.type === 'if' && fmtIfEvaluations(tr.debug)}
                  {tr.error && (
                    <span className={`block ${isStopped ? 'text-amber-700' : 'text-destructive'}`}>{tr.error}</span>
                  )}
                </TableCell>
              </TableRow>
            )})}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
}
