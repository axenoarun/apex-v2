import { NavLink, Outlet, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getProject } from '../api/endpoints';
import clsx from 'clsx';
import {
  Gauge,
  LayoutDashboard,
  ListChecks,
  Database,
  FileText,
  HelpCircle,
  MessageSquare,
  BarChart3,
  ScrollText,
  Bot,
  BookOpen,
} from 'lucide-react';

const tabs = [
  { path: 'dashboard', label: 'Dashboard', icon: Gauge },
  { path: 'phases', label: 'Phases', icon: LayoutDashboard },
  { path: 'tasks', label: 'Tasks', icon: ListChecks },
  { path: 'sources', label: 'Sources', icon: Database },
  { path: 'documents', label: 'Documents', icon: FileText },
  { path: 'questions', label: 'Questions', icon: HelpCircle },
  { path: 'feedback', label: 'Feedback', icon: MessageSquare },
  { path: 'executions', label: 'AI Agents', icon: Bot },
  { path: 'knowledge', label: 'Knowledge', icon: BookOpen },
  { path: 'costs', label: 'Costs', icon: BarChart3 },
  { path: 'audit', label: 'Audit', icon: ScrollText },
];

export default function ProjectDetail() {
  const { id: projectId } = useParams<{ id: string }>();
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => getProject(projectId!).then((r) => r.data),
    enabled: !!projectId,
  });

  if (!project) return <div className="p-8 text-slate-500">Loading project...</div>;

  return (
    <div>
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-8 pt-6 pb-0">
        <div className="mb-4">
          <h1 className="text-xl font-bold text-slate-900">{project.name}</h1>
          <p className="text-sm text-slate-500">{project.client_name}</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 -mb-px overflow-x-auto">
          {tabs.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={`/projects/${projectId}/${path}`}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-1.5 px-3 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                  isActive
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                )
              }
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div className="p-8">
        <Outlet context={{ project, projectId }} />
      </div>
    </div>
  );
}
