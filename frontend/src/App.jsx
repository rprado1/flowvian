import { useState } from 'react';
import { Toaster } from 'sonner';
import { WorkflowProvider, useWorkflow } from '@/context/WorkflowContext';
import TopBar    from '@/components/TopBar';
import AppSidebar from '@/components/AppSidebar';
import Canvas    from '@/components/Canvas';
import PropsPanel from '@/components/PropsPanel';
import RunPanel  from '@/components/RunPanel';
import NewWorkflowModal from '@/components/modals/NewWorkflowModal';
import RenameModal      from '@/components/modals/RenameModal';
import BuildLogModal    from '@/components/modals/BuildLogModal';
import { api } from '@/api';
import { toast } from 'sonner';
import { useBuild } from '@/hooks/useBuild';

function AppInner() {
  const { currentWfId, saveGraph, nodes, edges } = useWorkflow();
  const { building, buildExe } = useBuild();

  const [showNewWf,   setShowNewWf]   = useState(false);
  const [showRename,  setShowRename]  = useState(false);
  const [running,     setRunning]     = useState(false);
  const [runTraces,   setRunTraces]   = useState([]);
  const [runOutput,   setRunOutput]   = useState('');
  const [runFinalOutput, setRunFinalOutput] = useState(null);
  const [showRun,     setShowRun]     = useState(false);
  const [buildLog,    setBuildLog]    = useState(null); // { title, content, success, downloadUrl }

  // ── Save ─────────────────────────────────────────────────────────────
  const handleSave = async () => {
    await saveGraph(nodes, edges);
    toast.success('Saved');
  };

  // ── Preview ──────────────────────────────────────────────────────────
  const handlePreview = async () => {
    if (!currentWfId) return toast.error('Open a workflow first');
    await saveGraph(nodes, edges);
    try {
      const data = await api('POST', `/api/workflows/${currentWfId}/preview`);
      setBuildLog({ title: 'Generated Python Script', content: data.script, success: false });
    } catch (e) {
      toast.error(e.message);
    }
  };

  // ── Run ──────────────────────────────────────────────────────────────
  const handleRun = async () => {
    if (!currentWfId) return toast.error('Open a workflow first');
    await saveGraph(nodes, edges);
    setRunning(true);
    toast.info('Executing workflow…');
    try {
      const data = await api('POST', `/api/workflows/${currentWfId}/run`);
      setRunTraces(data.traces || []);
      setRunOutput(data.output || '');
      setRunFinalOutput(data.final_output || null);
      setShowRun(true);
      if (data.error) toast.error('Execution finished with errors');
      else toast.success('Execution completed');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setRunning(false);
    }
  };

  // ── Build ─────────────────────────────────────────────────────────────
  const handleBuild = async () => {
    if (!currentWfId) return toast.error('Open a workflow first');
    await saveGraph(nodes, edges);
    toast.info('Building .exe — this may take a minute…');
    buildExe(currentWfId, {
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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TopBar
        onRename={() => setShowRename(true)}
        onPreview={handlePreview}
        onSave={handleSave}
        onRun={handleRun}
        onBuild={handleBuild}
        running={running}
        building={building}
      />

      <div id="layout">
        <AppSidebar onNewWorkflow={() => setShowNewWf(true)} />

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

      {/* Modals */}
      <NewWorkflowModal open={showNewWf} onClose={() => setShowNewWf(false)} />
      <RenameModal      open={showRename} onClose={() => setShowRename(false)} />
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

export default function App() {
  return (
    <WorkflowProvider>
      <Toaster position="bottom-right" theme="dark" richColors />
      <AppInner />
    </WorkflowProvider>
  );
}
