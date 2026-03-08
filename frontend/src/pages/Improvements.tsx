import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listImprovements, reviewImprovement, listProjects } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { Lightbulb, Check, X } from 'lucide-react';

export default function Improvements() {
  const qc = useQueryClient();
  const [selectedProject, setSelectedProject] = useState('');

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => listProjects().then((r) => r.data),
  });

  const { data: improvements, isLoading } = useQuery({
    queryKey: ['improvements', selectedProject],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (selectedProject) params.project_id = selectedProject;
      return listImprovements(params).then((r) => r.data);
    },
  });

  const reviewMut = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) =>
      reviewImprovement(id, { approved, reviewer_notes: '' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['improvements'] }),
  });

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Lightbulb size={24} className="text-slate-700" />
          <h1 className="text-2xl font-bold text-slate-900">Improvement Proposals</h1>
        </div>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">All Projects</option>
          {projects?.map((p: any) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {isLoading && <div className="text-slate-500 text-sm">Loading improvements...</div>}

      <div className="space-y-3">
        {improvements?.map((imp: any) => (
          <div key={imp.id} className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                    {imp.category}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    imp.priority === 'HIGH' || imp.priority === 'CRITICAL'
                      ? 'bg-red-100 text-red-700'
                      : imp.priority === 'MEDIUM'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-slate-100 text-slate-600'
                  }`}>
                    {imp.priority}
                  </span>
                  <StatusBadge status={imp.status} />
                </div>
                <p className="text-sm text-slate-900 font-medium">{imp.title}</p>
                <p className="text-sm text-slate-600 mt-1">{imp.description}</p>
              </div>
              {imp.status === 'PROPOSED' && (
                <div className="flex gap-1 shrink-0 ml-4">
                  <button
                    onClick={() => reviewMut.mutate({ id: imp.id, approved: true })}
                    className="p-1.5 rounded hover:bg-green-50 text-green-600"
                    title="Approve"
                  >
                    <Check size={16} />
                  </button>
                  <button
                    onClick={() => reviewMut.mutate({ id: imp.id, approved: false })}
                    className="p-1.5 rounded hover:bg-red-50 text-red-600"
                    title="Reject"
                  >
                    <X size={16} />
                  </button>
                </div>
              )}
            </div>
            {imp.expected_impact && (
              <p className="text-xs text-slate-500 mt-2">Expected impact: {imp.expected_impact}</p>
            )}
            <p className="text-xs text-slate-400 mt-1">
              Source: {imp.source_type} | {new Date(imp.created_at).toLocaleString()}
            </p>
          </div>
        ))}
        {(!improvements || improvements.length === 0) && !isLoading && (
          <div className="text-center py-12 text-slate-400 text-sm">No improvement proposals yet.</div>
        )}
      </div>
    </div>
  );
}
