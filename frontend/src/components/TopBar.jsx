import { Button } from '@/components/ui/button';
import { useWorkflow } from '@/context/WorkflowContext';

export default function TopBar({
  onRename, onPreview, onSave, onRun, onBuild,
  onBackToWorkspaces,
  running, building,
}) {
  const { currentWfName, currentWfId } = useWorkflow();

  return (
    <header
      className="flex items-center gap-3 px-4 border-b border-border"
      style={{ height: 'var(--topbar-h)', flexShrink: 0, background: 'hsl(var(--card))' }}
    >
      <span className="font-bold text-sm text-primary mr-2">⚡ WorkflowEXE</span>

      {onBackToWorkspaces && (
        <Button variant="outline" size="sm" onClick={onBackToWorkspaces}>
          ← Workspaces
        </Button>
      )}

      <button
        className="text-sm font-medium text-foreground hover:text-primary transition-colors cursor-pointer bg-transparent border-0"
        onClick={() => currentWfId && onRename?.()}
        title="Click to rename"
      >
        {currentWfName || '—'}
      </button>

      <div className="flex-1" />

      <Button variant="outline" size="sm" onClick={onPreview} disabled={!currentWfId}>
        Preview Code
      </Button>
      <Button variant="outline" size="sm" onClick={onSave} disabled={!currentWfId}>
        Save
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={onRun}
        disabled={!currentWfId || running}
        className="text-[var(--accent-green)] border-[var(--accent-green)] hover:bg-[var(--accent-green)]/10"
      >
        {running ? 'Running…' : '▶ Run'}
      </Button>
      <Button
        size="sm"
        onClick={onBuild}
        disabled={!currentWfId || building}
      >
        {building ? 'Building…' : '⚙ Generate EXE'}
      </Button>
    </header>
  );
}
