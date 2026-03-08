import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Projects from './pages/Projects';
import ProjectDetail from './pages/ProjectDetail';
import DashboardTab from './pages/DashboardTab';
import PhasesTab from './pages/PhasesTab';
import TasksTab from './pages/TasksTab';
import SourcesTab from './pages/SourcesTab';
import DocumentsTab from './pages/DocumentsTab';
import QuestionsTab from './pages/QuestionsTab';
import FeedbackTab from './pages/FeedbackTab';
import CostsTab from './pages/CostsTab';
import AuditTab from './pages/AuditTab';
import Notifications from './pages/Notifications';
import Improvements from './pages/Improvements';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/projects" replace />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/:id" element={<ProjectDetail />}>
            <Route index element={<Navigate to="dashboard" replace />} />
            <Route path="dashboard" element={<DashboardTab />} />
            <Route path="phases" element={<PhasesTab />} />
            <Route path="tasks" element={<TasksTab />} />
            <Route path="sources" element={<SourcesTab />} />
            <Route path="documents" element={<DocumentsTab />} />
            <Route path="questions" element={<QuestionsTab />} />
            <Route path="feedback" element={<FeedbackTab />} />
            <Route path="costs" element={<CostsTab />} />
            <Route path="audit" element={<AuditTab />} />
          </Route>
          <Route path="notifications" element={<Notifications />} />
          <Route path="improvements" element={<Improvements />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
