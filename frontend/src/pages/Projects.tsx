import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { listProjects, createProject, updateProject, listProjectPhases } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import StatusBadge from '../components/StatusBadge';
import { Plus, FolderKanban, Trash2, X, Clock, BarChart3, Search } from 'lucide-react';

interface Phase {
  id: string;
  phase_name?: string;
  name?: string;
  status: string;
  order_index?: number;
}

interface Project {
  id: string;
  name: string;
  client_name: string;
  status: string;
  description?: string;
  created_at: string;
  updated_at?: string;
}

function PhaseProgressBar({ projectId }: { projectId: string }) {
  const { data: phases, isLoading } = useQuery({
    queryKey: ['project-phases', projectId],
    queryFn: () => listProjectPhases(projectId).then((r) => r.data),
    staleTime: 60000,
  });

  if (isLoading) {
    return <div className="h-2 bg-slate-100 rounded-full overflow-hidden w-full mt-2" />;
  }

  if (!phases || phases.length === 0) {
    return (
      <div className="mt-2">
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden w-full">
          <div className="h-full bg-slate-200 rounded-full" style={{ width: '0%' }} />
        </div>
        <p className="text-xs text-slate-400 mt-1">No phases initialized</p>
      </div>
    );
  }

  const total = phases.length;
  const completed = phases.filter(
    (p: Phase) => p.status === 'COMPLETED' || p.status === 'FINAL'
  ).length;
  const inProgress = phases.filter((p: Phase) => p.status === 'IN_PROGRESS').length;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;

  const currentPhase = phases.find((p: Phase) => p.status === 'IN_PROGRESS') ||
    phases.find((p: Phase) => p.status !== 'COMPLETED' && p.status !== 'FINAL');

  return (
    <div className="mt-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-500">
          {currentPhase
            ? `Current: ${currentPhase.phase_name || currentPhase.name || 'Phase'}`
            : completed === total
              ? 'All phases complete'
              : 'Not started'}
        </span>
        <span className="text-xs font-medium text-slate-600">
          {completed}/{total} phases ({pct}%)
        </span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden w-full flex">
        {completed > 0 && (
          <div
            className="h-full bg-green-500 transition-all duration-500"
            style={{ width: `${(completed / total) * 100}%` }}
          />
        )}
        {inProgress > 0 && (
          <div
            className="h-full bg-blue-400 transition-all duration-500"
            style={{ width: `${(inProgress / total) * 100}%` }}
          />
        )}
      </div>
    </div>
  );
}

export default function Projects() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState({ name: '', client_name: '', description: '' });

  const { data: projects, isLoading, dataUpdatedAt } = useQuery({
    queryKey: ['projects'],
    queryFn: () => listProjects().then((r) => r.data),
  });

  const createMut = useMutation({
    mutationFn: () =>
      createProject({
        organization_id: user!.organization_id,
        name: form.name,
        client_name: form.client_name,
        description: form.description || undefined,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] });
      setShowCreate(false);
      setForm({ name: '', client_name: '', description: '' });
    },
  });

  const archiveMut = useMutation({
    mutationFn: (id: string) => updateProject(id, { status: 'ARCHIVED' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['projects'] });
    },
  });

  const handleDelete = (e: React.MouseEvent, projectId: string, projectName: string) => {
    e.stopPropagation();
    if (window.confirm(`Archive project "${projectName}"? This will mark it as archived.`)) {
      archiveMut.mutate(projectId);
    }
  };

  const filteredProjects = projects?.filter((p: Project) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      p.name.toLowerCase().includes(q) ||
      p.client_name.toLowerCase().includes(q) ||
      (p.description && p.description.toLowerCase().includes(q))
    );
  });

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-200 rounded w-48" />
          <div className="h-4 bg-slate-100 rounded w-64" />
          <div className="space-y-3 mt-6">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-32 bg-slate-100 rounded-xl" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-sm text-slate-500">AA to CJA migration projects</p>
            {projects && (
              <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-full font-medium">
                {projects.length} project{projects.length !== 1 ? 's' : ''}
              </span>
            )}
            {dataUpdatedAt > 0 && (
              <span className="flex items-center gap-1 text-xs text-slate-400">
                <Clock size={12} />
                Updated {new Date(dataUpdatedAt).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors shadow-sm"
        >
          <Plus size={16} /> New Project
        </button>
      </div>

      {/* Search bar */}
      {projects && projects.length > 0 && (
        <div className="relative mb-6">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white"
            placeholder="Search projects by name, client, or description..."
          />
        </div>
      )}

      {/* Modal Overlay for Create */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 p-6 relative">
            <button
              onClick={() => setShowCreate(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 transition-colors"
            >
              <X size={20} />
            </button>
            <h2 className="text-lg font-semibold text-slate-900 mb-1">Create New Project</h2>
            <p className="text-sm text-slate-500 mb-5">
              Set up a new AA to CJA migration project for your client.
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Project Name <span className="text-red-500">*</span>
                </label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="e.g., Acme Corp CJA Migration"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Client Name <span className="text-red-500">*</span>
                </label>
                <input
                  value={form.client_name}
                  onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  placeholder="e.g., Acme Corp"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none"
                  rows={3}
                  placeholder="Brief description of the migration scope and goals..."
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => {
                  setShowCreate(false);
                  setForm({ name: '', client_name: '', description: '' });
                }}
                className="border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => createMut.mutate()}
                disabled={!form.name.trim() || !form.client_name.trim() || createMut.isPending}
                className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {createMut.isPending ? 'Creating...' : 'Create Project'}
              </button>
            </div>
            {createMut.isError && (
              <p className="text-sm text-red-600 mt-3">
                Failed to create project. Please try again.
              </p>
            )}
          </div>
        </div>
      )}

      {/* Project Cards */}
      <div className="grid gap-4">
        {filteredProjects?.map((p: Project) => (
          <div
            key={p.id}
            onClick={() => navigate(`/projects/${p.id}`)}
            className="bg-white rounded-xl border border-slate-200 p-5 cursor-pointer hover:border-blue-300 hover:shadow-md transition-all group"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <div className="p-2 bg-blue-50 rounded-lg mt-0.5 group-hover:bg-blue-100 transition-colors">
                  <FolderKanban size={20} className="text-blue-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-slate-900 truncate">{p.name}</h3>
                    <StatusBadge status={p.status} />
                  </div>
                  <p className="text-sm text-slate-500 mt-0.5">{p.client_name}</p>
                  {p.description && (
                    <p className="text-sm text-slate-400 mt-1 line-clamp-2">{p.description}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 ml-4 shrink-0">
                <span className="text-xs text-slate-400">
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
                <button
                  onClick={(e) => handleDelete(e, p.id, p.name)}
                  disabled={archiveMut.isPending}
                  className="p-1.5 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                  title="Archive project"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
            <div className="ml-11">
              <PhaseProgressBar projectId={p.id} />
            </div>
          </div>
        ))}

        {/* Empty state after search */}
        {filteredProjects && filteredProjects.length === 0 && search && (
          <div className="text-center py-12 text-slate-400">
            <Search size={40} className="mx-auto mb-3 opacity-50" />
            <p className="font-medium text-slate-500">No projects match "{search}"</p>
            <p className="text-sm mt-1">Try adjusting your search terms.</p>
          </div>
        )}

        {/* Empty state — no projects at all */}
        {projects && projects.length === 0 && (
          <div className="text-center py-16 text-slate-400">
            <div className="inline-flex p-4 bg-slate-100 rounded-2xl mb-4">
              <BarChart3 size={40} className="text-slate-400" />
            </div>
            <h3 className="text-lg font-semibold text-slate-600 mb-1">No projects yet</h3>
            <p className="text-sm max-w-sm mx-auto mb-6">
              Create your first AA to CJA migration project to get started. You will be able to
              configure phases, assign tasks, and track progress.
            </p>
            <button
              onClick={() => setShowCreate(true)}
              className="inline-flex items-center gap-2 bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              <Plus size={16} /> Create Your First Project
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
