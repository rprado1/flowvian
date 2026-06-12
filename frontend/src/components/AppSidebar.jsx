import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useWorkflow } from '@/context/WorkflowContext';
import { NODE_META } from '@/nodes';
import DeleteModal from './modals/DeleteModal';

export default function AppSidebar({ onNewWorkflow }) {
  const { workflows, currentWfId, openWorkflow, loadWorkflows } = useWorkflow();
  const [delTarget, setDelTarget] = useState(null); // { id, name }

  useEffect(() => {
    loadWorkflows().catch(() => {});
  }, [loadWorkflows]);

  return (
    <aside
      className="flex flex-col border-r border-border overflow-hidden"
      style={{ width: 'var(--sidebar-w)', flexShrink: 0, background: 'hsl(var(--card))' }}
    >
      {/* Workflows section */}
      <div className="p-3 flex flex-col gap-2 flex-1 overflow-hidden">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Workflows
          </span>
          <Button variant="outline" size="sm" className="h-6 px-2 text-xs" onClick={onNewWorkflow}>
            + New
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1">
          {workflows.length === 0 && (
            <p className="text-xs text-muted-foreground px-1 py-2">No workflows yet</p>
          )}
          {workflows.map(wf => (
            <div
              key={wf.id}
              className={`wf-item ${wf.id === currentWfId ? 'active' : ''}`}
              onClick={() => openWorkflow(wf.id, wf.name)}
            >
              <span className="truncate text-sm">{wf.name}</span>
              <button
                className="text-muted-foreground hover:text-destructive transition-colors ml-1 text-base leading-none"
                title="Delete"
                onClick={e => { e.stopPropagation(); setDelTarget({ id: wf.id, name: wf.name }); }}
              >
                🗑
              </button>
            </div>
          ))}
        </div>

        <Separator className="my-2 bg-border" />

        {/* Node palette */}
        <div>
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground block mb-2">
            Nodes
          </span>
          <div className="space-y-2">
            {Object.entries(NODE_META).map(([type, meta]) => (
              <div
                key={type}
                className="palette-node"
                draggable
                onDragStart={e => e.dataTransfer.setData('node-type', type)}
              >
                <span className="palette-node-icon">{meta.icon}</span>
                <div>
                  <div className="font-semibold text-xs leading-tight">{meta.label}</div>
                  <div className="text-xs text-muted-foreground leading-tight">{meta.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Delete confirm modal */}
      {delTarget && (
        <DeleteModal
          open={!!delTarget}
          wfId={delTarget.id}
          wfName={delTarget.name}
          onClose={() => setDelTarget(null)}
          onDeleted={() => setDelTarget(null)}
        />
      )}
    </aside>
  );
}
