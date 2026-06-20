import { useState } from 'react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

function fmtItems(items) {
  if (!items || !Array.isArray(items) || !items.length) {
    return <span className="text-muted-foreground">—</span>;
  }
  
  return (
    <span className="block">
      <span className="text-muted-foreground text-xs">
        {items.length} item{items.length !== 1 ? 's' : ''}
      </span>
      {items.slice(0, 3).map((item, idx) => {
        const entries = Object.entries(item).slice(0, 5);
        return (
          <span key={idx} className="block text-xs mt-1 pl-2 border-l-2 border-border">
            {entries.map(([k, v]) => {
              let val = String(v ?? '');
              if (val.length > 40) val = val.substring(0, 37) + '…';
              return (
                <span key={k} className="block">
                  <code className="run-ctx">{k}</code> = {val}
                </span>
              );
            })}
            {Object.keys(item).length > 5 && (
              <span className="text-muted-foreground">+{Object.keys(item).length - 5} more</span>
            )}
          </span>
        );
      })}
      {items.length > 3 && (
        <span className="text-xs text-muted-foreground pl-2">
          +{items.length - 3} more items
        </span>
      )}
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
            <div className="text-xs text-muted-foreground mb-1">
              <code className="run-ctx">{branchId}</code>
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
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="w-8 text-muted-foreground">#</TableHead>
              <TableHead className="text-muted-foreground">Node</TableHead>
              <TableHead className="text-muted-foreground">Type</TableHead>
              <TableHead className="text-muted-foreground">Time</TableHead>
              <TableHead className="text-muted-foreground">Status</TableHead>
              <TableHead className="text-muted-foreground">Items In</TableHead>
              <TableHead className="text-muted-foreground">Items Out</TableHead>
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
              return (
              <TableRow key={i} className={`border-border ${rowClass}`}>
                <TableCell className="text-xs">{i + 1}</TableCell>
                <TableCell className="text-xs font-semibold">{tr.label || tr.id || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{tr.type || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {tr.ts ? new Date(tr.ts * 1000).toLocaleTimeString() : '—'}
                </TableCell>
                <TableCell className="text-xs">
                  {tr.status === 'ok' ? '✅' : (isStopped ? '🛑' : '❌')} {tr.status}
                </TableCell>
                <TableCell className="text-xs">{fmtItems(tr.items_in)}</TableCell>
                <TableCell className="text-xs">
                  {fmtItems(tr.items_out)}
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
