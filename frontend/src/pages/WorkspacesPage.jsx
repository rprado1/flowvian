import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useWorkflow } from '@/context/WorkflowContext';
import NewWorkflowModal from '@/components/modals/NewWorkflowModal';
import DeleteModal from '@/components/modals/DeleteModal';

export default function WorkspacesPage() {
  const navigate = useNavigate();
  const { workflows, loadWorkflows, renameWorkflow } = useWorkflow();

  const [query, setQuery] = useState('');
  const [showNewWf, setShowNewWf] = useState(false);
  const [renameTarget, setRenameTarget] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);

  useEffect(() => {
    loadWorkflows().catch(() => {
      toast.error('Could not load workspaces');
    });
  }, [loadWorkflows]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return workflows;
    return workflows.filter(wf => `${wf.name} ${wf.description || ''}`.toLowerCase().includes(q));
  }, [workflows, query]);

  const openRename = (wf) => {
    setRenameTarget(wf);
    setRenameValue(wf.name || '');
  };

  const submitRename = async () => {
    if (!renameTarget) return;
    const nextName = renameValue.trim();
    if (!nextName) return toast.error('Enter a workspace name');
    setRenaming(true);
    try {
      await renameWorkflow(renameTarget.id, nextName);
      toast.success('Workspace renamed');
      setRenameTarget(null);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setRenaming(false);
    }
  };

  return (
    <div className="h-screen overflow-hidden flex flex-col bg-background text-foreground">
      <header className="h-[var(--topbar-h)] border-b border-border flex items-center px-4 gap-3 bg-card">
        <span className="font-bold text-sm text-primary">⚡ WorkflowEXE</span>
        <div className="flex-1" />
        <Button size="sm" onClick={() => setShowNewWf(true)}>+ New Workspace</Button>
      </header>

      <main className="flex-1 overflow-hidden p-4 md:p-6">
        <div className="h-full rounded-lg border border-border bg-card p-4 md:p-5 flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div>
              <h1 className="text-lg font-semibold">Workspaces</h1>
              <p className="text-xs text-muted-foreground">Manage workspaces and open one to edit its workflow graph.</p>
            </div>
            <div className="flex-1" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search workspace..."
              className="w-full max-w-xs"
            />
          </div>

          <div className="flex-1 min-h-0 rounded-md border border-border/70 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="w-[230px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={3} className="text-sm text-muted-foreground">No workspaces found.</TableCell>
                  </TableRow>
                )}

                {filtered.map(wf => (
                  <TableRow key={wf.id}>
                    <TableCell className="font-medium">{wf.name}</TableCell>
                    <TableCell className="text-muted-foreground">{wf.description || '—'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button size="sm" className="bg-sky-600 text-white hover:bg-sky-700" onClick={() => navigate(`/editor/${wf.id}`)}>Open</Button>
                        <Button variant="outline" size="sm" onClick={() => openRename(wf)}>Rename</Button>
                        <Button variant="destructive" size="sm" onClick={() => setDeleteTarget(wf)}>Delete</Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </main>

      <NewWorkflowModal open={showNewWf} onClose={() => setShowNewWf(false)} />

      <Dialog open={!!renameTarget} onOpenChange={(v) => !v && setRenameTarget(null)}>
        <DialogContent className="bg-card border-border text-foreground">
          <DialogHeader>
            <DialogTitle>Rename Workspace</DialogTitle>
          </DialogHeader>
          <div className="py-2">
            <Input
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitRename()}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameTarget(null)} disabled={renaming}>Cancel</Button>
            <Button onClick={submitRename} disabled={renaming}>{renaming ? 'Saving…' : 'Rename'}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {deleteTarget && (
        <DeleteModal
          open={!!deleteTarget}
          wfId={deleteTarget.id}
          wfName={deleteTarget.name}
          onClose={() => setDeleteTarget(null)}
          onDeleted={() => setDeleteTarget(null)}
        />
      )}
    </div>
  );
}
