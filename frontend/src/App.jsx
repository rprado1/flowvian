import { Toaster } from 'sonner';
import { Navigate, Route, Routes } from 'react-router-dom';
import { WorkflowProvider } from '@/context/WorkflowContext';
import WorkspacesPage from '@/pages/WorkspacesPage';
import EditorPage from '@/pages/EditorPage';

export default function App() {
  return (
    <WorkflowProvider>
      <Toaster position="bottom-right" theme="dark" richColors />
      <Routes>
        <Route path="/" element={<Navigate to="/workspaces" replace />} />
        <Route path="/workspaces" element={<WorkspacesPage />} />
        <Route path="/editor/:workflowId" element={<EditorPage />} />
        <Route path="*" element={<Navigate to="/workspaces" replace />} />
      </Routes>
    </WorkflowProvider>
  );
}
