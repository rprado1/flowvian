import { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';
import { useNodesState, useEdgesState } from 'reactflow';
import { NODE_META } from '@/nodes';
import { api } from '@/api';
import { toast } from 'sonner';

const WorkflowContext = createContext(null);

export function WorkflowProvider({ children }) {
  const [recentNodeTypes, setRecentNodeTypes] = useState(() => {
    if (typeof window === 'undefined') return [];
    try {
      const raw = window.localStorage.getItem('workflowexe.recentNodeTypes');
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed.filter(v => typeof v === 'string') : [];
    } catch {
      return [];
    }
  });
  const [workflows, setWorkflows]             = useState([]);
  const [currentWfId, setCurrentWfId]         = useState(null);
  const [currentWfName, setCurrentWfName]     = useState('');
  const [selectedNodeId, setSelectedNodeId]   = useState(null);
  const [nodes, setNodes, onNodesChange]       = useNodesState([]);
  const [edges, setEdges, onEdgesChange]       = useEdgesState([]);
  const saveTimer                              = useRef(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem('workflowexe.recentNodeTypes', JSON.stringify(recentNodeTypes));
    } catch {
      // noop
    }
  }, [recentNodeTypes]);

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
    const nodeLookup = new Map((currentNodes || nodes).map(n => [String(n.id), n]));
    const apiNodes = (currentNodes || nodes).map(n => ({
      id:     n.id,
      type:   n.type,
      label:  n.data.instanceName || NODE_META[n.type]?.label || n.type,
      pos_x:  n.position.x,
      pos_y:  n.position.y,
      config: n.data.config || {},
    }));
    const apiEdges = (currentEdges || edges)
      .filter(e => {
        if (!e.sourceHandle || !e.targetHandle) return false;
        const targetNode = nodeLookup.get(String(e.target));
        if (!targetNode) return false;
        if (targetNode.type === 'merge') {
          return /^in-\d+$/.test(e.targetHandle);
        }
        return true;
      })
      .map(e => ({
        id:             e.id,
        source_node_id: e.source,
        target_node_id: e.target,
        source_output:  e.sourceHandle,
        target_input:   e.targetHandle,
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
    const dbNodeTypeById = new Map((data.nodes || []).map(n => [String(n.id), n.type]));
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
      targetHandle: e.target_input || (dbNodeTypeById.get(String(e.target_node_id)) === 'merge' ? undefined : 'input_1'),
    }));
    setNodes(rfNodes);
    setEdges(rfEdges);
    setSelectedNodeId(null);
  }, [setNodes, setEdges]);

  const pushRecentNodeType = useCallback((type) => {
    setRecentNodeTypes(prev => {
      return [type, ...prev.filter(v => v !== type)].slice(0, 8);
    });
  }, []);

  const clearRecentNodeTypes = useCallback(() => {
    setRecentNodeTypes([]);
    try {
      window.localStorage.removeItem('workflowexe.recentNodeTypes');
    } catch {
      // noop
    }
  }, []);

  const addNode = useCallback((type, position) => {
    if (!currentWfId) return false;
    if (!NODE_META[type]) return false;

    const fallbackPosition = {
      x: 120 + ((nodes.length % 5) * 60),
      y: 120 + ((nodes.length % 6) * 50),
    };

    const nextId = `${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;

    setNodes(prev => {
      const instanceName = generateInstanceName(type, prev);
      const newNode = {
        id: nextId,
        type,
        position: position || fallbackPosition,
        data: {
          instanceName,
          config: NODE_META[type].defaultConfig(),
        },
      };
      const next = [...prev, newNode];
      scheduleSave(next, edges);
      return next;
    });

    setSelectedNodeId(nextId);
    pushRecentNodeType(type);
    return true;
  }, [currentWfId, nodes.length, setNodes, generateInstanceName, scheduleSave, edges, setSelectedNodeId, pushRecentNodeType]);

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

  const renameWorkflow = useCallback(async (id, name, description) => {
    const updated = await api('PUT', `/api/workflows/${id}`, { name, description });
    setWorkflows(prev => prev.map(w => (w.id === id ? {
      ...w,
      name: updated.name,
      description: updated.description,
    } : w)));
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
      addNode,
      recentNodeTypes,
      clearRecentNodeTypes,
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
