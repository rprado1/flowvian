import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

function fmtCtx(ctx) {
  if (!ctx || typeof ctx !== 'object') return null;
  const entries = Object.entries(ctx).filter(([k]) => !k.startsWith('_')).slice(0, 20);
  if (!entries.length) return null;
  return entries.map(([k, v]) => {
    let val = String(v ?? '');
    if (val.length > 60) val = val.substring(0, 57) + '…';
    return (
      <span key={k} className="block">
        <code className="run-ctx">{k}</code> = {val}
      </span>
    );
  });
}

export default function RunPanel({ traces, output, onClose }) {
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
          <pre className="build-log-pre mx-4 mt-2 text-xs" style={{ maxHeight: 80 }}>{output}</pre>
        )}
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-transparent">
              <TableHead className="w-8 text-muted-foreground">#</TableHead>
              <TableHead className="text-muted-foreground">Node</TableHead>
              <TableHead className="text-muted-foreground">Type</TableHead>
              <TableHead className="text-muted-foreground">Time</TableHead>
              <TableHead className="text-muted-foreground">Status</TableHead>
              <TableHead className="text-muted-foreground">Input</TableHead>
              <TableHead className="text-muted-foreground">Output</TableHead>
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
            {traces.map((tr, i) => (
              <TableRow key={i} className={`border-border ${tr.status === 'error' ? 'run-err' : 'run-ok'}`}>
                <TableCell className="text-xs">{i + 1}</TableCell>
                <TableCell className="text-xs font-semibold">{tr.label || tr.id || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{tr.type || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {tr.ts ? new Date(tr.ts * 1000).toLocaleTimeString() : '—'}
                </TableCell>
                <TableCell className="text-xs">
                  {tr.status === 'ok' ? '✅' : '❌'} {tr.status}
                </TableCell>
                <TableCell className="text-xs">{fmtCtx(tr.input) || <span className="text-muted-foreground">—</span>}</TableCell>
                <TableCell className="text-xs">
                  {fmtCtx(tr.output) || <span className="text-muted-foreground">—</span>}
                  {tr.status === 'error' && tr.error && (
                    <span className="block text-destructive">{tr.error}</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </ScrollArea>
    </div>
  );
}
