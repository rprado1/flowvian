import { useEffect, useState } from 'react';
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
import RenameModal from '@/components/modals/RenameModal';
import { useBuild } from '@/hooks/useBuild';

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
  const [runStateMsg, setRunStateMsg] = useState('');

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
    await saveGraph(nodes, edges);
    try {
      const data = await api('POST', `/api/workflows/${workflowId}/preview`);
      setBuildLog({ title: 'Generated Python Script', content: data.script, success: false });
    } catch (e) {
      toast.error(e.message);
    }
  };

  const handleRun = async () => {
    if (!workflowId) return toast.error('Open a workspace first');
    await saveGraph(nodes, edges);
    setRunning(true);
    setRunStateMsg('Starting run...');
    toast.info('Executing workflow…');

    const pollState = async () => {
      try {
        const st = await api('GET', `/api/workflows/${workflowId}/run/state`);
        if (st?.status === 'running') {
          if (st.phase === 'waiting_webhook') {
            const method = st.method || 'POST';
            const host = st.host || '127.0.0.1';
            const port = st.port || '';
            const path = st.path || '/webhook';
            setRunStateMsg(`Waiting webhook: ${method} http://${host}${port ? `:${port}` : ''}${path}`);
          } else if (st.phase === 'executing_workflow') {
            setRunStateMsg('Webhook received, executing workflow...');
          } else {
            setRunStateMsg('Running...');
          }
        }
      } catch {
        // ignore state polling errors
      }
    };

    const stateTimer = window.setInterval(pollState, 1000);
    void pollState();

    try {
      const data = await api('POST', `/api/workflows/${workflowId}/run`);
      setRunTraces(data.traces || []);
      setRunOutput(data.output || '');
      setRunFinalOutput(data.final_output || null);
      setShowRun(true);
      if (data.error) toast.error('Execution finished with errors');
      else toast.success('Execution completed');
    } catch (e) {
      toast.error(e.message);
    } finally {
      window.clearInterval(stateTimer);
      setRunning(false);
      setRunStateMsg('');
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

  const handleBuild = async () => {
    if (!workflowId) return toast.error('Open a workspace first');
    await saveGraph(nodes, edges);
    toast.info('Building .exe — this may take a minute…');
    buildExe(workflowId, {
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
        onBuild={handleBuild}
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
