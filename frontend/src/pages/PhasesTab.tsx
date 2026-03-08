import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listProjectPhases, getPhaseDetail, evaluateGate, advancePhase, overrideAdvance, rollbackPhase } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { useState } from 'react';
import { ChevronRight, Shield, RotateCcw, Play } from 'lucide-react';

export default function PhasesTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [selectedPhase, setSelectedPhase] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState('');

  const { data: phases } = useQuery({
    queryKey: ['phases', projectId],
    queryFn: () => listProjectPhases(projectId).then((r) => r.data),
  });

  const { data: detail } = useQuery({
    queryKey: ['phase-detail', selectedPhase],
    queryFn: () => getPhaseDetail(selectedPhase!).then((r) => r.data),
    enabled: !!selectedPhase,
  });

  const gateMut = useMutation({
    mutationFn: (phaseId: string) => evaluateGate(phaseId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['phases'] }),
  });

  const advanceMut = useMutation({
    mutationFn: () => advancePhase(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases'] });
      qc.invalidateQueries({ queryKey: ['project'] });
    },
  });

  const overrideMut = useMutation({
    mutationFn: () => overrideAdvance(projectId, overrideReason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases'] });
      qc.invalidateQueries({ queryKey: ['project'] });
      setOverrideReason('');
    },
  });

  const rollbackMut = useMutation({
    mutationFn: () => rollbackPhase(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases'] });
      qc.invalidateQueries({ queryKey: ['project'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Phase Workflow</h2>
        <div className="flex gap-2">
          <button
            onClick={() => advanceMut.mutate()}
            disabled={advanceMut.isPending}
            className="flex items-center gap-1.5 bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-green-700 disabled:opacity-50"
          >
            <Play size={14} /> Advance Phase
          </button>
          <button
            onClick={() => rollbackMut.mutate()}
            disabled={rollbackMut.isPending}
            className="flex items-center gap-1.5 border border-red-300 text-red-600 px-3 py-1.5 rounded-lg text-sm hover:bg-red-50 disabled:opacity-50"
          >
            <RotateCcw size={14} /> Rollback
          </button>
        </div>
      </div>

      {/* Phase list */}
      <div className="space-y-3">
        {phases?.map((phase: any, i: number) => (
          <div
            key={phase.id}
            onClick={() => setSelectedPhase(phase.id)}
            className={`bg-white rounded-xl border p-4 cursor-pointer transition-all ${
              selectedPhase === phase.id ? 'border-blue-400 shadow-sm' : 'border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  phase.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                  phase.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                  'bg-slate-100 text-slate-500'
                }`}>
                  {i + 1}
                </div>
                <span className="font-medium text-slate-900">Phase {i + 1}</span>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={phase.status} />
                {phase.status === 'IN_PROGRESS' && (
                  <button
                    onClick={(e) => { e.stopPropagation(); gateMut.mutate(phase.id); }}
                    className="flex items-center gap-1 text-xs bg-indigo-50 text-indigo-600 px-2 py-1 rounded hover:bg-indigo-100"
                  >
                    <Shield size={12} /> Evaluate Gate
                  </button>
                )}
                <ChevronRight size={16} className="text-slate-400" />
              </div>
            </div>

            {phase.gate_results && (
              <div className="mt-3 pl-11">
                <div className="flex flex-wrap gap-2">
                  {Object.entries(phase.gate_results).map(([key, val]: any) => (
                    <span key={key} className={`text-xs px-2 py-0.5 rounded ${val ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                      {key.replace(/_/g, ' ')}: {val ? '✓' : '✗'}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Gate override */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h3 className="text-sm font-semibold text-slate-700 mb-2">Gate Override</h3>
        <div className="flex gap-2">
          <input
            value={overrideReason}
            onChange={(e) => setOverrideReason(e.target.value)}
            placeholder="Override reason..."
            className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
          />
          <button
            onClick={() => overrideMut.mutate()}
            disabled={!overrideReason || overrideMut.isPending}
            className="bg-amber-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-amber-700 disabled:opacity-50"
          >
            Override & Advance
          </button>
        </div>
      </div>

      {/* Phase detail */}
      {detail && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-900 mb-3">
            {detail.phase_name} — {detail.task_instances?.length || 0} Tasks
          </h3>
          <div className="space-y-2">
            {detail.task_instances?.map((t: any) => (
              <div key={t.id} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                <span className="text-sm text-slate-700">{t.id.slice(0, 8)}...</span>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">{t.classification}</span>
                  <StatusBadge status={t.status} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
