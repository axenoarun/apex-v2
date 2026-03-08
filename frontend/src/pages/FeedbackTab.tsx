import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listFeedback, submitFeedback, listExecutions, analyzeFeedback } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { MessageSquare, Plus, Sparkles, BarChart3, AlertTriangle, ThumbsUp, ThumbsDown } from 'lucide-react';

const CATEGORIES = ['ACCURACY', 'COMPLETENESS', 'FORMATTING', 'RELEVANCE', 'OTHER'] as const;
const SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const;

export default function FeedbackTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState('ALL');
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

  const analyzeMut = useMutation({
    mutationFn: () => analyzeFeedback(projectId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['improvements'] }),
  });

  // Stats
  const total = feedback?.length || 0;
  const avgScore = total > 0 ? (feedback.reduce((s: number, f: any) => s + (f.quality_score || 0), 0) / total) : 0;
  const criticalCount = feedback?.filter((f: any) => f.severity === 'CRITICAL' || f.severity === 'HIGH').length || 0;
  const byCat = feedback?.reduce((acc: Record<string, number>, f: any) => {
    acc[f.category] = (acc[f.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  const filtered = filter === 'ALL' ? feedback : feedback?.filter((f: any) => f.category === filter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Feedback</h2>
        <div className="flex gap-2">
          <button
            onClick={() => analyzeMut.mutate()}
            disabled={analyzeMut.isPending || total === 0}
            className="flex items-center gap-1.5 bg-purple-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
          >
            <Sparkles size={14} /> {analyzeMut.isPending ? 'Analyzing...' : 'Analyze with AI'}
          </button>
          <button onClick={() => setShowForm(true)} className="flex items-center gap-1.5 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-blue-700">
            <Plus size={14} /> Submit Feedback
          </button>
        </div>
      </div>

      {analyzeMut.isSuccess && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-700">
          Feedback analysis queued. Check the Improvements tab for generated proposals.
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <MessageSquare size={14} className="text-slate-500" />
          </div>
          <div className="text-2xl font-bold text-slate-700">{total}</div>
          <div className="text-xs text-slate-500">Total</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <BarChart3 size={14} className="text-blue-500" />
          </div>
          <div className="text-2xl font-bold text-blue-600">{avgScore.toFixed(2)}</div>
          <div className="text-xs text-slate-500">Avg Score</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            <AlertTriangle size={14} className="text-red-500" />
          </div>
          <div className="text-2xl font-bold text-red-600">{criticalCount}</div>
          <div className="text-xs text-slate-500">High/Critical</div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
          <div className="flex items-center justify-center gap-1 mb-1">
            {avgScore >= 0.6 ? <ThumbsUp size={14} className="text-green-500" /> : <ThumbsDown size={14} className="text-orange-500" />}
          </div>
          <div className="text-2xl font-bold text-slate-700">
            {total > 0 ? `${Math.round((feedback.filter((f: any) => f.quality_score >= 0.7).length / total) * 100)}%` : '—'}
          </div>
          <div className="text-xs text-slate-500">Positive Rate</div>
        </div>
      </div>

      {/* Category breakdown */}
      {Object.keys(byCat).length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <span className="text-xs font-medium text-slate-500 mb-2 block">By Category</span>
          <div className="flex gap-2 flex-wrap">
            {Object.entries(byCat).map(([cat, count]) => (
              <button
                key={cat}
                onClick={() => setFilter(filter === cat ? 'ALL' : cat)}
                className={`px-2 py-1 rounded text-xs ${
                  filter === cat ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {cat}: {count as number}
              </button>
            ))}
            {filter !== 'ALL' && (
              <button onClick={() => setFilter('ALL')} className="px-2 py-1 rounded text-xs text-blue-600 hover:underline">
                Clear filter
              </button>
            )}
          </div>
        </div>
      )}

      {showForm && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <h3 className="font-medium text-slate-900">Submit Feedback</h3>
          <select value={form.agent_execution_id} onChange={(e) => setForm({ ...form, agent_execution_id: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
            <option value="">Select Agent Execution</option>
            {executions?.map((e: any) => <option key={e.id} value={e.id}>{e.id.slice(0, 8)}... ({e.status})</option>)}
          </select>
          <div className="grid grid-cols-3 gap-3">
            <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm">
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={form.severity} onChange={(e) => setForm({ ...form, severity: e.target.value })} className="border border-slate-300 rounded-lg px-3 py-2 text-sm">
              {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <div>
              <input type="number" min="0" max="1" step="0.1" value={form.quality_score} onChange={(e) => setForm({ ...form, quality_score: parseFloat(e.target.value) })} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" placeholder="Score 0-1" />
            </div>
          </div>
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" rows={3} placeholder="Describe the issue..." />
          <div className="flex gap-2">
            <button onClick={() => submitMut.mutate()} disabled={!form.agent_execution_id || !form.description} className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm disabled:opacity-50">Submit</button>
            <button onClick={() => setShowForm(false)} className="text-sm text-slate-500">Cancel</button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        {filtered?.map((fb: any) => (
          <div key={fb.id} className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <MessageSquare size={16} className="text-blue-500" />
                <span className="text-sm font-medium">{fb.category}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  fb.severity === 'CRITICAL' ? 'bg-red-100 text-red-700'
                  : fb.severity === 'HIGH' ? 'bg-orange-100 text-orange-700'
                  : fb.severity === 'MEDIUM' ? 'bg-amber-100 text-amber-700'
                  : 'bg-slate-100 text-slate-600'
                }`}>{fb.severity}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1">
                  <div className={`w-2 h-2 rounded-full ${fb.quality_score >= 0.7 ? 'bg-green-500' : fb.quality_score >= 0.4 ? 'bg-amber-500' : 'bg-red-500'}`} />
                  <span className="text-sm font-medium">{fb.quality_score}</span>
                </div>
              </div>
            </div>
            <p className="text-sm text-slate-700">{fb.description}</p>
            <p className="text-xs text-slate-400 mt-1">{new Date(fb.created_at).toLocaleString()}</p>
          </div>
        ))}
        {(!filtered || filtered.length === 0) && <div className="text-center py-8 text-slate-400 text-sm">No feedback submitted yet.</div>}
      </div>
    </div>
  );
}
