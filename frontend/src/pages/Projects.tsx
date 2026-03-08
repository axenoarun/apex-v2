import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { listProjects, createProject } from '../api/endpoints';
import { useAuth } from '../context/AuthContext';
import StatusBadge from '../components/StatusBadge';
import { Plus, FolderKanban } from 'lucide-react';

export default function Projects() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: '', client_name: '', description: '' });

  const { data: projects, isLoading } = useQuery({
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

  if (isLoading) return <div className="p-8 text-slate-500">Loading projects...</div>;

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Projects</h1>
          <p className="text-sm text-slate-500 mt-1">AA → CJA migration projects</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          <Plus size={16} /> New Project
        </button>
      </div>

      {showCreate && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Create Project</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Project Name</label>
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                placeholder="e.g., Acme Corp CJA Migration"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Client Name</label>
              <input
                value={form.client_name}
                onChange={(e) => setForm({ ...form, client_name: e.target.value })}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                placeholder="e.g., Acme Corp"
              />
            </div>
          </div>
          <div className="mt-4">
            <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
              rows={2}
            />
          </div>
          <div className="flex gap-2 mt-4">
            <button
              onClick={() => createMut.mutate()}
              disabled={!form.name || !form.client_name || createMut.isPending}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {createMut.isPending ? 'Creating...' : 'Create Project'}
            </button>
            <button
              onClick={() => setShowCreate(false)}
              className="border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {projects?.map((p: any) => (
          <div
            key={p.id}
            onClick={() => navigate(`/projects/${p.id}`)}
            className="bg-white rounded-xl border border-slate-200 p-5 cursor-pointer hover:border-blue-300 hover:shadow-sm transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <FolderKanban size={20} className="text-blue-600" />
                <div>
                  <h3 className="font-semibold text-slate-900">{p.name}</h3>
                  <p className="text-sm text-slate-500">{p.client_name}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={p.status} />
                <span className="text-xs text-slate-400">
                  {new Date(p.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
            {p.description && (
              <p className="text-sm text-slate-500 mt-2 ml-8">{p.description}</p>
            )}
          </div>
        ))}
        {projects?.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <FolderKanban size={40} className="mx-auto mb-3 opacity-50" />
            <p>No projects yet. Create your first migration project.</p>
          </div>
        )}
      </div>
    </div>
  );
}
