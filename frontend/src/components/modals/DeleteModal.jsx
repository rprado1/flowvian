import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useWorkflow } from '@/context/WorkflowContext';

export default function DeleteModal({ open, wfId, wfName, onClose, onDeleted }) {
  const { deleteWorkflow } = useWorkflow();
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    setLoading(true);
    try {
      await deleteWorkflow(wfId);
      toast.success('Workflow deleted');
      onDeleted?.();
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
          <DialogTitle>Delete Workflow</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground py-2">
          Delete <strong className="text-foreground">"{wfName}"</strong>? This cannot be undone.
        </p>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button variant="destructive" onClick={handleDelete} disabled={loading}>
            {loading ? 'Deleting…' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
