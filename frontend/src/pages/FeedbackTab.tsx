import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listFeedback, submitFeedback, listExecutions } from '../api/endpoints';
import { MessageSquare, Plus } from 'lucide-react';

export default function FeedbackTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ agent_execution_id: '', category: 'ACCURACY', severity: 'MEDIUM', description: '', quality_score: 0.5 });

  const { data: feedback } = useQuery({
    queryKey: ['feedback', projectId],
    queryFn: () => listFeedback({ project_id: projectId }).then((r) => r.data),
  });

  const { data: executions } = useQuery({
    queryKey: ['executions', projectId],
    queryFn: () => listExecutions({ project_id: projectId }).then((r) => r.data),
    enabled: showForm,
  });

  const submitMut = useMutation({
    mutationFn: () =>
      submitFeedback({
        project_id: projectId,
        agent_execution_id: form.agent_execution_id,
        category: form.category,
        severity: form.severity,
        description: form.description,
        quality_score: form.quality_score,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['feedback'] });
      setShowForm(false);
      setForm({ agent_execution_id: '', category: 'ACCURACY', severity: 'MEDIUM', description: '', quality_score: 0.5 });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Feedback</h2>
        <button onClick={() => setShowForm(true)} className="flex items-center gap-1.5 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-blue-700">
          <Plus size={14} /> Submit Feedback
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <select value={form.agent_execution_id} onChange={(e) => setForm({ ...form, agent_execution_id: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
            <option value="">Select Agent Execution</option>
            {executions?.map((e: any) => <option key={e.id} value={e.id}>{e.id.slice(0, 8)}... ({e.status})</option>)}
          </select>
          <div className="grid grid-cols-3 gap-3">
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm">
              {['ACCURACY', 'COMPLETENESS', 'FORMATTING', 'RELEVANCE', 'OTHER'].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm">
              {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <input type="number" min="0" max="1" step="0.1" value={form.quality_score} onChange={(e) => setForm({ ...form, quality_score: parseFloat(e.target.value) })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm" placeholder="Score 0-1" />
          </div>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" rows={3} placeholder="Describe the issue..." />
          <div className="flex gap-2">
            <button onClick={() => submitMut.mutate()} disabled={!form.agent_execution_id || !form.description} className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm disabled:opacity-50">Submit</button>
            <button onClick={() => setShowForm(false)} className="text-sm text-slate-500">Cancel</button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {feedback?.map((fb: any) => (
          <div key={fb.id} className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-blue-500" />
                <span className="text-sm font-medium">{fb.category}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${fb.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' : fb.severity === 'HIGH' ? 'bg-orange-100 text-orange-700' : 'bg-slate-100 text-slate-600'}`}>{fb.severity}</span>
              </div>
              <span className="text-sm font-medium">Score: {fb.quality_score}</span>
            </div>
            <p className="text-sm text-slate-700">{fb.description}</p>
            <p className="text-xs text-slate-400 mt-1">{new Date(fb.created_at).toLocaleString()}</p>
          </div>
        ))}
        {(!feedback || feedback.length === 0) && <div className="text-center py-8 text-slate-400 text-sm">No feedback submitted yet.</div>}
      </div>
    </div>
  );
}
