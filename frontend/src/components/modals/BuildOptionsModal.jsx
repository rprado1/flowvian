import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

export default function BuildOptionsModal({
  open,
  onClose,
  onBuildNormal,
  onBuildDebug,
  building,
}) {
  return (
    <Dialog open={open} onOpenChange={v => !v && onClose()}>
      <DialogContent className="bg-card border-border text-foreground max-w-md">
        <DialogHeader>
          <DialogTitle>Generate EXE</DialogTitle>
        </DialogHeader>
        <div className="text-sm text-muted-foreground space-y-2">
          <p>Choose how you want to generate the executable:</p>
          <p>
            <strong>Without debug</strong>: standard build and download.
          </p>
          <p>
            <strong>With debug</strong>: standard build plus a runtime log that saves
            the full run results table after each scheduler iteration.
          </p>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={building}>Cancel</Button>
          <Button variant="outline" onClick={onBuildNormal} disabled={building}>
            Download without debug
          </Button>
          <Button onClick={onBuildDebug} disabled={building}>
            Download with debug
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
