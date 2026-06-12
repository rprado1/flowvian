import { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { useWorkflow } from '@/context/WorkflowContext';

export default function RenameModal({ open, onClose }) {
  const { currentWfId, currentWfName, renameWorkflow } = useWorkflow();
  const [name, setName]     = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { if (open) setName(currentWfName); }, [open, currentWfName]);

  const handleRename = async () => {
    if (!name.trim()) return toast.error('Enter a name');
    setLoading(true);
    try {
      await renameWorkflow(currentWfId, name.trim());
      toast.success('Renamed');
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
          <DialogTitle>Rename Workflow</DialogTitle>
        </DialogHeader>
        <div className="py-2">
          <div className="prop-group">
            <Label>New name</Label>
            <Input
              autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleRename()}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={loading}>Cancel</Button>
          <Button onClick={handleRename} disabled={loading}>
            {loading ? 'Saving…' : 'Rename'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
