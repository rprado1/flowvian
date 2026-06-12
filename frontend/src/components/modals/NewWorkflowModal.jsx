import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useWorkflow } from '@/context/WorkflowContext';

export default function NewWorkflowModal({ open, onClose }) {
  const { createWorkflow } = useWorkflow();
  const [name, setName]     = useState('');
  const [desc, setDesc]     = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async () => {
    if (!name.trim()) return toast.error('Enter a workflow name');
    setLoading(true);
    try {
      await createWorkflow(name.trim(), desc.trim());
      toast.success(`Workflow "${name}" created`);
      setName(''); setDesc('');
      onClose();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="bg-card border-border text-foreground">
        <DialogHeader>
          <DialogTitle>New Workflow</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div className="prop-group">
            <Label>Name</Label>
            <Input
              autoFocus
              placeholder="My workflow"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleCreate()}
            />
          </div>
          <div className="prop-group">
            <Label>Description (optional)</Label>
            <Input
              placeholder="What does this workflow do?"
              value={desc}
              onChange={e => setDesc(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button onClick={handleCreate} disabled={loading}>
            {loading ? 'Creating…' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
