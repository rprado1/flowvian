import { useWorkflow } from '@/context/WorkflowContext';
import { NODE_META } from '@/nodes';
import { ScrollArea } from '@/components/ui/scroll-area';

export default function PropsPanel() {
  const { nodes, setNodes, selectedNodeId, setSelectedNodeId, scheduleSave } = useWorkflow();

  const selectedNode = selectedNodeId != null
    ? nodes.find(n => n.id === String(selectedNodeId))
    : null;

  if (!selectedNode) return null;

  const meta = NODE_META[selectedNode.type];
  const PropsForm = meta?.PropsForm;

  const handleConfigChange = (newConfig) => {
    setNodes(prev => prev.map(n =>
      n.id === selectedNode.id
        ? { ...n, data: { ...n.data, config: newConfig } }
        : n
    ));
    scheduleSave();
  };

  return (
    <aside
      id="props-panel"
      className="flex flex-col border-l border-border"
      style={{ width: 'var(--props-w)', flexShrink: 0, background: 'hsl(var(--card))' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-sm font-semibold truncate">
          {meta?.icon} {selectedNode.data.instanceName}
        </h3>
        <button
          className="text-muted-foreground hover:text-foreground transition-colors text-lg leading-none"
          onClick={() => setSelectedNodeId(null)}
          title="Close"
        >
          ×
        </button>
      </div>

      {/* Form */}
      <ScrollArea className="flex-1 p-4">
        {PropsForm ? (
          <PropsForm
            config={selectedNode.data.config || {}}
            onChange={handleConfigChange}
          />
        ) : (
          <p className="text-xs text-muted-foreground">No properties for this node.</p>
        )}
      </ScrollArea>
    </aside>
  );
}
