import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

export default function BuildLogModal({ open, onClose, title, content, success, downloadUrl }) {
  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="bg-card border-border text-foreground max-w-2xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <pre className="build-log-pre">{content}</pre>
        <DialogFooter>
          {success && downloadUrl && (
            <Button
              variant="outline"
              className="text-[var(--accent-green)] border-[var(--accent-green)]"
              onClick={() => { window.location.href = downloadUrl; }}
            >
              Download EXE
            </Button>
          )}
          <Button onClick={onClose}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
