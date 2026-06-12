import { useCallback, useRef } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useWorkflow } from '@/context/WorkflowContext';
import { nodeTypes, NODE_META } from '@/nodes';

function FlowCanvas() {
  const {
    nodes, edges,
    onNodesChange, onEdgesChange,
    setNodes, setEdges,
    selectedNodeId, setSelectedNodeId,
    generateInstanceName,
    scheduleSave,
    currentWfId,
  } = useWorkflow();

  const { project } = useReactFlow();
  const wrapperRef = useRef(null);

  // ── Drag-drop from palette ───────────────────────────────────────────
  const onDragOver = useCallback(e => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(e => {
    e.preventDefault();
    if (!currentWfId) return;
    const type = e.dataTransfer.getData('node-type');
    if (!type || !NODE_META[type]) return;

    const bounds = wrapperRef.current?.getBoundingClientRect();
    const position = project({
      x: e.clientX - (bounds?.left ?? 0),
      y: e.clientY - (bounds?.top ?? 0),
    });

    const instanceName = generateInstanceName(type, nodes);
    const newNode = {
      id:       String(Date.now()),
      type,
      position,
      data: {
        instanceName,
        config: NODE_META[type].defaultConfig(),
      },
    };

    setNodes(prev => {
      const next = [...prev, newNode];
      scheduleSave(next, edges);
      return next;
    });
  }, [currentWfId, nodes, edges, project, generateInstanceName, setNodes, scheduleSave]);

  // ── Node selection ───────────────────────────────────────────────────
  const onNodeClick = useCallback((_, node) => {
    setSelectedNodeId(node.id);
  }, [setSelectedNodeId]);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
  }, [setSelectedNodeId]);

  // ── Node deletion (Delete key — native React Flow + our handler) ─────
  const onNodesDelete = useCallback(deletedNodes => {
    const deletedIds = new Set(deletedNodes.map(n => n.id));
    if (deletedIds.has(String(selectedNodeId))) {
      setSelectedNodeId(null);
    }
  }, [selectedNodeId, setSelectedNodeId]);

  // ── Changes with auto-save ───────────────────────────────────────────
  const handleNodesChange = useCallback(changes => {
    onNodesChange(changes);
    scheduleSave();
  }, [onNodesChange, scheduleSave]);

  const handleEdgesChange = useCallback(changes => {
    onEdgesChange(changes);
    scheduleSave();
  }, [onEdgesChange, scheduleSave]);

  const onConnect = useCallback(params => {
    setEdges(prev => {
      const next = [...prev, {
        id:           `${params.source}_${params.target}_${params.sourceHandle}_${params.targetHandle}`,
        source:       params.source,
        target:       params.target,
        sourceHandle: params.sourceHandle,
        targetHandle: params.targetHandle,
      }];
      scheduleSave(nodes, next);
      return next;
    });
  }, [nodes, setEdges, scheduleSave]);

  return (
    <div
      ref={wrapperRef}
      style={{ flex: 1, position: 'relative' }}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={handleNodesChange}
        onEdgesChange={handleEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodesDelete={onNodesDelete}
        deleteKeyCode="Delete"
        fitView
        minZoom={0.2}
        maxZoom={2}
      >
        <Background color="hsl(221 38% 25% / 0.4)" gap={20} size={1} />
        <Controls />
        <MiniMap
          nodeColor={() => 'hsl(214 75% 22%)'}
          maskColor="hsl(222 47% 11% / 0.7)"
        />
      </ReactFlow>

      {!currentWfId && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-muted-foreground text-sm">Select or create a workflow</p>
        </div>
      )}
    </div>
  );
}

export default function Canvas() {
  return (
    <ReactFlowProvider>
      <FlowCanvas />
    </ReactFlowProvider>
  );
}
