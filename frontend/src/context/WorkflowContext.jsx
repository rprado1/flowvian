import { createContext, useContext, useState, useRef, useCallback } from 'react';
import { useNodesState, useEdgesState } from 'reactflow';
import { NODE_META } from '@/nodes';
import { api } from '@/api';
import { toast } from 'sonner';

const WorkflowContext = createContext(null);

export function WorkflowProvider({ children }) {
  const [workflows, setWorkflows]             = useState([]);
  const [currentWfId, setCurrentWfId]         = useState(null);
  const [currentWfName, setCurrentWfName]     = useState('');
  const [selectedNodeId, setSelectedNodeId]   = useState(null);
  const [nodes, setNodes, onNodesChange]       = useNodesState([]);
  const [edges, setEdges, onEdgesChange]       = useEdgesState([]);
  const saveTimer                              = useRef(null);

  // ── Instance name generation ──────────────────────────────────────────
  const generateInstanceName = useCallback((type, currentNodes) => {
    const baseName = NODE_META[type]?.label || type;
    const used = new Set((currentNodes || nodes).map(n => n.data?.instanceName).filter(Boolean));
    if (!used.has(baseName)) return baseName;
    for (let n = 2; n < 9999; n++) {
      const candidate = `${baseName} ${n}`;
      if (!used.has(candidate)) return candidate;
    }
    return baseName;
  }, [nodes]);

  // ── Graph persistence ─────────────────────────────────────────────────
  const saveGraph = useCallback(async (currentNodes, currentEdges, wfId) => {
    const id = wfId || currentWfId;
    if (!id) return;
    const apiNodes = (currentNodes || nodes).map(n => ({
      id:     n.id,
      type:   n.type,
      label:  n.data.instanceName || NODE_META[n.type]?.label || n.type,
      pos_x:  n.position.x,
      pos_y:  n.position.y,
      config: n.data.config || {},
    }));
    const apiEdges = (currentEdges || edges).map(e => ({
      id:             e.id,
      source_node_id: e.source,
      target_node_id: e.target,
      source_output:  e.sourceHandle || 'output_1',
      target_input:   e.targetHandle || 'input_1',
    }));
    try {
      await api('POST', `/api/workflows/${id}/graph`, { nodes: apiNodes, edges: apiEdges });
    } catch (e) {
      toast.error('Auto-save failed: ' + e.message);
    }
  }, [currentWfId, nodes, edges]);

  const scheduleSave = useCallback((currentNodes, currentEdges) => {
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => saveGraph(currentNodes, currentEdges), 800);
  }, [saveGraph]);

  const loadGraph = useCallback(async (wfId) => {
    const data = await api('GET', `/api/workflows/${wfId}/graph`);
    const rfNodes = (data.nodes || []).map(n => {
      const meta = NODE_META[n.type];
      return {
        id:       String(n.id),
        type:     n.type,
        position: { x: n.pos_x, y: n.pos_y },
        data: {
          instanceName: (n.label && n.label !== n.type) ? n.label : (meta?.label || n.type),
          config:       n.config || meta?.defaultConfig() || {},
        },
      };
    });
    const rfEdges = (data.edges || []).map(e => ({
      id:           e.id,
      source:       String(e.source_node_id),
      target:       String(e.target_node_id),
      sourceHandle: e.source_output  || 'output_1',
      targetHandle: e.target_input   || 'input_1',
    }));
    setNodes(rfNodes);
    setEdges(rfEdges);
    setSelectedNodeId(null);
  }, [setNodes, setEdges]);

  // ── Workflow CRUD ─────────────────────────────────────────────────────
  const loadWorkflows = useCallback(async () => {
    const data = await api('GET', '/api/workflows/');
    setWorkflows(data);
    return data;
  }, []);

  const openWorkflow = useCallback(async (id, name) => {
    setCurrentWfId(id);
    setCurrentWfName(name);
    setSelectedNodeId(null);
    await loadGraph(id);
  }, [loadGraph]);

  const createWorkflow = useCallback(async (name, description) => {
    const wf = await api('POST', '/api/workflows/', { name, description });
    setWorkflows(prev => [wf, ...prev]);
    await openWorkflow(wf.id, wf.name);
    return wf;
  }, [openWorkflow]);

  const renameWorkflow = useCallback(async (id, name) => {
    const updated = await api('PUT', `/api/workflows/${id}`, { name });
    setWorkflows(prev => prev.map(w => w.id === id ? { ...w, name: updated.name } : w));
    if (id === currentWfId) setCurrentWfName(updated.name);
    return updated;
  }, [currentWfId]);

  const deleteWorkflow = useCallback(async (id) => {
    await api('DELETE', `/api/workflows/${id}`);
    setWorkflows(prev => {
      const next = prev.filter(w => w.id !== id);
      return next;
    });
    if (id === currentWfId) {
      setCurrentWfId(null);
      setCurrentWfName('');
      setNodes([]);
      setEdges([]);
      setSelectedNodeId(null);
    }
  }, [currentWfId, setNodes, setEdges]);

  return (
    <WorkflowContext.Provider value={{
      workflows, setWorkflows,
      currentWfId, currentWfName,
      selectedNodeId, setSelectedNodeId,
      nodes, setNodes, onNodesChange,
      edges, setEdges, onEdgesChange,
      generateInstanceName,
      saveGraph, scheduleSave, loadGraph,
      loadWorkflows, openWorkflow,
      createWorkflow, renameWorkflow, deleteWorkflow,
    }}>
      {children}
    </WorkflowContext.Provider>
  );
}

export function useWorkflow() {
  const ctx = useContext(WorkflowContext);
  if (!ctx) throw new Error('useWorkflow must be used inside WorkflowProvider');
  return ctx;
}
