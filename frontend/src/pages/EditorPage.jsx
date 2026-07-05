import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { api } from '@/api';
import { useWorkflow } from '@/context/WorkflowContext';
import TopBar from '@/components/TopBar';
import AppSidebar from '@/components/AppSidebar';
import Canvas from '@/components/Canvas';
import PropsPanel from '@/components/PropsPanel';
import RunPanel from '@/components/RunPanel';
import BuildLogModal from '@/components/modals/BuildLogModal';
import BuildOptionsModal from '@/components/modals/BuildOptionsModal';
import RenameModal from '@/components/modals/RenameModal';
import { useBuild } from '@/hooks/useBuild';

function getTriggerDiagnostics(nodes) {
  const triggerTypes = new Set(['webhook', 'scheduler']);
  const triggerNodes = (nodes || []).filter((node) => triggerTypes.has(String(node?.type || '')));
  return {
    count: triggerNodes.length,
    triggerNodes,
  };
}

export default function EditorPage() {
  const navigate = useNavigate();
  const { workflowId } = useParams();
  const { currentWfId, openWorkflow, saveGraph, nodes, edges } = useWorkflow();
  const { building, buildExe } = useBuild();

  const [loadingWorkspace, setLoadingWorkspace] = useState(true);
  const [showRename, setShowRename] = useState(false);
  const [running, setRunning] = useState(false);
  const [runTraces, setRunTraces] = useState([]);
  const [runOutput, setRunOutput] = useState('');
  const [runFinalOutput, setRunFinalOutput] = useState(null);
  const [showRun, setShowRun] = useState(false);
  const [buildLog, setBuildLog] = useState(null);
  const [showBuildOptions, setShowBuildOptions] = useState(false);
  const [runStateMsg, setRunStateMsg] = useState('');
  const runStateTimerRef = useRef(null);

  const ensureExecutableTrigger = () => {
    const diagnostics = getTriggerDiagnostics(nodes);
    if (diagnostics.count === 0) {
      toast.error('El workflow debe tener un trigger (Webhook o Scheduler) para ejecutarse.');
      return false;
    }
    if (diagnostics.count > 1) {
      toast.error('Solo se permite un trigger por workflow.');
      return false;
    }
    return true;
  };

  const handleExportTemplate = async () => {
    if (!workflowId) return toast.error('Open a workspace first');
    try {
      await saveGraph(nodes, edges);
      const payload = await api('GET', `/api/workflows/${workflowId}/template/export`);
      const workflowName = String(payload?.workflow?.name || 'workflow').trim() || 'workflow';
      const safe = workflowName.replace(/[^a-z0-9-_]+/gi, '_').replace(/^_+|_+$/g, '') || 'workflow';
      const fileName = `workflow-template-${safe}.json`;
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = fileName;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success('Template exported');
    } catch (e) {
      toast.error(e.message || 'Export failed');
    }
  };

  const handleImportTemplate = async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'application/json,.json';
    input.onchange = async () => {
      const file = input.files && input.files[0];
      if (!file) return;
      try {
        const text = await file.text();
        let payload;
        try {
          payload = JSON.parse(text);
        } catch {
          toast.error('Invalid JSON file');
          return;
        }
        const res = await api('POST', '/api/workflows/template/import', payload);
        const warnings = Array.isArray(res?.warnings) ? res.warnings : [];
        if (warnings.length) {
          toast.warning(`Imported with warnings (${warnings.length})`);
        } else {
          toast.success('Template imported');
        }
        const nextId = res?.workflow?.id;
        if (nextId) {
          navigate(`/editor/${nextId}`);
        }
      } catch (e) {
        if (Array.isArray(e?.detail?.errors) && e.detail.errors.length) {
          toast.error(e.detail.errors.slice(0, 2).join(' | '));
        } else {
          toast.error(e.message || 'Import failed');
        }
      }
    };
    input.click();
  };

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      if (!workflowId) {
        navigate('/workspaces', { replace: true });
        return;
      }

      setLoadingWorkspace(true);
      try {
        const wf = await api('GET', `/api/workflows/${workflowId}`);
        if (!mounted) return;
        await openWorkflow(wf.id, wf.name);
      } catch {
        if (!mounted) return;
        toast.error('Workspace not found');
        navigate('/workspaces', { replace: true });
      } finally {
        if (mounted) setLoadingWorkspace(false);
      }
    };

    if (workflowId !== currentWfId) {
      load();
    } else {
      setLoadingWorkspace(false);
    }

    return () => { mounted = false; };
  }, [workflowId, currentWfId, openWorkflow, navigate]);

  const handleSave = async () => {
    await saveGraph(nodes, edges);
    toast.success('Saved');
  };

  const handlePreview = async () => {
    if (!workflowId) return toast.error('Open a workspace first');
    if (!ensureExecutableTrigger()) return;
    await saveGraph(nodes, edges);
    try {
      const data = await api('POST', `/api/workflows/${workflowId}/preview`);
      setBuildLog({ title: 'Generated Python Script', content: data.script, success: false });
    } catch (e) {
      toast.error(e.message);
    }
  };

  const clearRunPolling = () => {
    if (runStateTimerRef.current) {
      window.clearInterval(runStateTimerRef.current);
      runStateTimerRef.current = null;
    }
  };

  const loadRunResultAndClose = async () => {
    try {
      const result = await api('GET', `/api/workflows/${workflowId}/run/result`);
      setRunTraces(result.traces || []);
      setRunOutput(result.output || '');
      setRunFinalOutput(result.final_output || null);
      setShowRun(true);
    } catch {
      // no-op: run result may not be available yet
    }
    setRunning(false);
    setRunStateMsg('');
    clearRunPolling();
  };

  const handleRun = async () => {
    if (!workflowId) return toast.error('Open a workspace first');
    if (!ensureExecutableTrigger()) return;
    await saveGraph(nodes, edges);
    setRunning(true);
    setRunStateMsg('Starting run...');
    toast.info('Executing workflow…');

    clearRunPolling();

    let hasSeenRunningState = false;

    const pollState = async () => {
      try {
        const st = await api('GET', `/api/workflows/${workflowId}/run/state`);
        if (st?.status === 'running') {
          hasSeenRunningState = true;
          if (st.phase === 'waiting_webhook') {
            const method = st.method || 'POST';
            const host = st.host || '127.0.0.1';
            const port = st.port || '';
            const path = st.path || '/webhook';
            setRunStateMsg(`Waiting webhook: ${method} http://${host}${port ? `:${port}` : ''}${path}`);
          } else if (st.phase === 'executing_workflow' || st.phase === 'webhook_request_received') {
            setRunStateMsg('Webhook received, executing workflow...');
          } else {
            setRunStateMsg('Running...');
          }
          return;
        }

        if (
          hasSeenRunningState
          && (st?.status === 'completed' || st?.status === 'error' || st?.status === 'stopped')
        ) {
          await loadRunResultAndClose();
        }
      } catch {
        // ignore state polling errors
      }
    };

    const timer = window.setInterval(pollState, 1000);
    runStateTimerRef.current = timer;
    void pollState();

    let keepPollingAfterRequest = false;

    try {
      const data = await api('POST', `/api/workflows/${workflowId}/run`);
      setRunTraces(data.traces || []);
      setRunOutput(data.output || '');
      setRunFinalOutput(data.final_output || null);
      setShowRun(true);
      if (data.error) toast.error('Execution finished with errors');
      else toast.success('Execution completed');
    } catch (e) {
      const isConflict = e?.message === 'A run is already in progress for this workflow';
      const isPortInUse = e?.detail?.phase === 'webhook_port_in_use';
      if (isConflict) {
        keepPollingAfterRequest = true;
        setRunning(true);
        setRunStateMsg('Re-attached to running workflow...');
        toast.info('A run is already in progress. Re-attached to current run.');
      } else if (isPortInUse) {
        toast.error(e.message);
      } else {
        toast.error(e.message);
      }
    } finally {
      if (!keepPollingAfterRequest) {
        clearRunPolling();
        setRunning(false);
        setRunStateMsg('');
      }
    }
  };

  const handleStopRun = async () => {
    if (!workflowId) return;
    try {
      const data = await api('POST', `/api/workflows/${workflowId}/run/stop`);
      toast.info(data?.message || 'Stop requested');
      setRunStateMsg('Stopping run...');
    } catch (e) {
      toast.error(e.message);
    }
  };

  useEffect(() => {
    return () => {
      if (runStateTimerRef.current) {
        window.clearInterval(runStateTimerRef.current);
      }
    };
  }, []);

  const handleBuild = async (debug = false) => {
    if (!workflowId) return toast.error('Open a workspace first');
    if (!ensureExecutableTrigger()) return;
    await saveGraph(nodes, edges);
    toast.info('Building .exe — this may take a minute…');
    buildExe(workflowId, {
      debug,
      onSuccess: (status) => {
        setBuildLog({ title: 'Build Successful ✓', content: status.log, success: true, downloadUrl: status.download_url });
        toast.success('EXE built successfully!');
      },
      onError: (msg, log) => {
        setBuildLog({ title: 'Build Failed', content: [msg, log].filter(Boolean).join('\n\n'), success: false });
        toast.error('Build failed');
      },
    });
  };

  const handleBuildChoice = async (debug) => {
    setShowBuildOptions(false);
    await handleBuild(debug);
  };

  if (loadingWorkspace) {
    return (
      <div className="h-screen flex items-center justify-center text-sm text-muted-foreground">
        Loading workspace...
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TopBar
        onBackToWorkspaces={() => navigate('/workspaces')}
        onRename={() => setShowRename(true)}
        onPreview={handlePreview}
        onSave={handleSave}
        onRun={handleRun}
        onStopRun={handleStopRun}
        onBuild={() => setShowBuildOptions(true)}
        onExportTemplate={handleExportTemplate}
        onImportTemplate={handleImportTemplate}
        running={running}
        runStateMsg={runStateMsg}
        building={building}
      />

      <div id="layout">
        <AppSidebar />

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Canvas />
          {showRun && (
            <RunPanel
              traces={runTraces}
              output={runOutput}
              finalOutput={runFinalOutput}
              onClose={() => setShowRun(false)}
            />
          )}
        </div>

        <PropsPanel />
      </div>

      <RenameModal open={showRename} onClose={() => setShowRename(false)} />
      <BuildOptionsModal
        open={showBuildOptions}
        onClose={() => setShowBuildOptions(false)}
        onBuildNormal={() => handleBuildChoice(false)}
        onBuildDebug={() => handleBuildChoice(true)}
        building={building}
      />
      {buildLog && (
        <BuildLogModal
          open={!!buildLog}
          onClose={() => setBuildLog(null)}
          title={buildLog.title}
          content={buildLog.content}
          success={buildLog.success}
          downloadUrl={buildLog.downloadUrl}
        />
      )}
    </div>
  );
}
