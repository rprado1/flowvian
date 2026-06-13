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
            {traces.map((tr, i) => (
              <TableRow key={i} className={`border-border ${tr.status !== 'ok' ? 'run-err' : 'run-ok'}`}>
                <TableCell className="text-xs">{i + 1}</TableCell>
                <TableCell className="text-xs font-semibold">{tr.label || tr.id || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{tr.type || '?'}</TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {tr.ts ? new Date(tr.ts * 1000).toLocaleTimeString() : '—'}
                </TableCell>
                <TableCell className="text-xs">
                  {tr.status === 'ok' ? '✅' : '❌'} {tr.status}
                </TableCell>
                <TableCell className="text-xs">{fmtItems(tr.items_in)}</TableCell>
                <TableCell className="text-xs">
                  {fmtItems(tr.items_out)}
                  {tr.error && (
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
