import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listProjectPhases,
  getPhaseDetail,
  evaluateGate,
  advancePhase,
  overrideAdvance,
  rollbackPhase,
  generateQuestions,
} from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { useState, useMemo } from 'react';
import {
  ChevronRight,
  ChevronDown,
  Shield,
  RotateCcw,
  Play,
  CheckCircle2,
  XCircle,
  Circle,
  Clock,
  Sparkles,
  AlertTriangle,
  Calendar,
  ListChecks,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface PhaseInstance {
  id: string;
  phase_definition_id?: string;
  phase_name?: string;
  description?: string;
  order_number?: number;
  status: string;
  started_at?: string;
  completed_at?: string;
  gate_criteria?: Record<string, unknown>[];
  gate_results?: Record<string, boolean>;
  gate_passed?: boolean;
  task_instances?: TaskInstance[];
}

interface TaskInstance {
  id: string;
  task_name?: string;
  classification?: string;
  status: string;
  assigned_to?: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function statusColor(status: string): { bg: string; ring: string; text: string; line: string } {
  switch (status) {
    case 'COMPLETED':
      return { bg: 'bg-green-500', ring: 'ring-green-200', text: 'text-green-700', line: 'bg-green-400' };
    case 'IN_PROGRESS':
      return { bg: 'bg-blue-500', ring: 'ring-blue-200', text: 'text-blue-700', line: 'bg-blue-400' };
    default:
      return { bg: 'bg-slate-300', ring: 'ring-slate-100', text: 'text-slate-500', line: 'bg-slate-200' };
  }
}

function formatDate(iso?: string): string {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function durationLabel(start?: string, end?: string): string {
  if (!start) return '';
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  const diffMs = e - s;
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 60) return `${diffMins}m`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ${diffMins % 60}m`;
  const diffDays = Math.floor(diffHrs / 24);
  return `${diffDays}d ${diffHrs % 24}h`;
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function MiniProgressBar({ completed, total }: { completed: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((completed / total) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-green-500 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-slate-500 whitespace-nowrap">
        {completed}/{total} tasks
      </span>
    </div>
  );
}

function GateCriteriaChecklist({
  criteria,
  results,
}: {
  criteria?: Record<string, unknown>[];
  results?: Record<string, boolean>;
}) {
  if (!criteria || criteria.length === 0) return null;

  return (
    <div className="mt-4">
      <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <ListChecks size={13} /> Gate Criteria
      </h4>
      <div className="space-y-1.5">
        {criteria.map((c: any, idx: number) => {
          const key = c.key || c.name || c.criterion || `criterion_${idx}`;
          const label = c.label || c.description || c.name || key;
          const passed = results ? results[key] : undefined;

          return (
            <div
              key={idx}
              className="flex items-start gap-2 py-1 px-2 rounded-md bg-slate-50"
            >
              {passed === true && <CheckCircle2 size={15} className="text-green-500 mt-0.5 shrink-0" />}
              {passed === false && <XCircle size={15} className="text-red-500 mt-0.5 shrink-0" />}
              {passed === undefined && <Circle size={15} className="text-slate-300 mt-0.5 shrink-0" />}
              <div className="min-w-0">
                <span className="text-sm text-slate-700">{String(label).replace(/_/g, ' ')}</span>
                {c.threshold !== undefined && (
                  <span className="ml-2 text-xs text-slate-400">threshold: {String(c.threshold)}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GateEvaluationResults({ results }: { results?: Record<string, boolean> }) {
  if (!results || Object.keys(results).length === 0) return null;

  const entries = Object.entries(results);
  const passed = entries.filter(([, v]) => v).length;
  const allPassed = passed === entries.length;

  return (
    <div className="mt-4 p-3 rounded-lg border border-slate-200 bg-white">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide flex items-center gap-1.5">
          <Shield size={13} /> Gate Evaluation Results
        </h4>
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            allPassed ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}
        >
          {allPassed ? 'PASSED' : `${passed}/${entries.length} passed`}
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
        {entries.map(([key, val]) => (
          <div
            key={key}
            className={`flex items-center gap-2 text-sm px-2 py-1.5 rounded-md ${
              val ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}
          >
            {val ? <CheckCircle2 size={14} /> : <XCircle size={14} />}
            <span className="truncate">{key.replace(/_/g, ' ')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TasksByClassification({ tasks }: { tasks: TaskInstance[] }) {
  const grouped = useMemo(() => {
    const map: Record<string, TaskInstance[]> = {};
    for (const t of tasks) {
      const cls = t.classification || 'uncategorized';
      if (!map[cls]) map[cls] = [];
      map[cls].push(t);
    }
    return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
  }, [tasks]);

  if (grouped.length === 0) {
    return <p className="text-sm text-slate-400 italic">No tasks in this phase.</p>;
  }

  return (
    <div className="space-y-4">
      {grouped.map(([cls, items]) => {
        const completed = items.filter((t) => t.status === 'COMPLETED').length;
        return (
          <div key={cls}>
            <div className="flex items-center justify-between mb-1.5">
              <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                {cls.replace(/_/g, ' ')}
              </h5>
              <span className="text-xs text-slate-400">
                {completed}/{items.length} done
              </span>
            </div>
            <div className="space-y-1">
              {items.map((t) => (
                <div
                  key={t.id}
                  className="flex items-center justify-between py-1.5 px-2 rounded-md bg-slate-50 hover:bg-slate-100 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {t.status === 'COMPLETED' ? (
                      <CheckCircle2 size={14} className="text-green-500 shrink-0" />
                    ) : t.status === 'IN_PROGRESS' || t.status === 'AI_PROCESSING' ? (
                      <Clock size={14} className="text-blue-500 shrink-0" />
                    ) : (
                      <Circle size={14} className="text-slate-300 shrink-0" />
                    )}
                    <span className="text-sm text-slate-700 truncate">
                      {t.task_name || t.id.slice(0, 12)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    {t.assigned_to && (
                      <span className="text-xs text-slate-400 truncate max-w-[100px]">
                        {t.assigned_to.slice(0, 8)}
                      </span>
                    )}
                    <StatusBadge status={t.status} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function PhasesTab() {
  const { projectId } = useOutletContext<{ projectId: string }>();
  const qc = useQueryClient();
  const [selectedPhase, setSelectedPhase] = useState<string | null>(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [showOverride, setShowOverride] = useState(false);

  /* ---- queries ---- */

  const { data: phases, isLoading: phasesLoading } = useQuery({
    queryKey: ['phases', projectId],
    queryFn: () => listProjectPhases(projectId).then((r) => r.data),
  });

  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['phase-detail', selectedPhase],
    queryFn: () => getPhaseDetail(selectedPhase!).then((r) => r.data),
    enabled: !!selectedPhase,
  });

  /* ---- mutations ---- */

  const gateMut = useMutation({
    mutationFn: (phaseId: string) => evaluateGate(phaseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases', projectId] });
      if (selectedPhase) qc.invalidateQueries({ queryKey: ['phase-detail', selectedPhase] });
    },
  });

  const advanceMut = useMutation({
    mutationFn: () => advancePhase(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases', projectId] });
      qc.invalidateQueries({ queryKey: ['project'] });
    },
  });

  const overrideMut = useMutation({
    mutationFn: () => overrideAdvance(projectId, overrideReason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases', projectId] });
      qc.invalidateQueries({ queryKey: ['project'] });
      setOverrideReason('');
      setShowOverride(false);
    },
  });

  const rollbackMut = useMutation({
    mutationFn: () => rollbackPhase(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases', projectId] });
      qc.invalidateQueries({ queryKey: ['project'] });
    },
  });

  const questionsMut = useMutation({
    mutationFn: (phaseInstanceId: string) => generateQuestions(projectId, phaseInstanceId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['phases', projectId] });
    },
  });

  /* ---- derived ---- */

  const phaseList: PhaseInstance[] = phases ?? [];
  const activePhase = phaseList.find((p) => p.status === 'IN_PROGRESS');
  const selectedPhaseData = phaseList.find((p) => p.id === selectedPhase);

  const detailTasks: TaskInstance[] = detail?.task_instances ?? [];
  const completedTasks = detailTasks.filter((t) => t.status === 'COMPLETED').length;
  const totalTasks = detailTasks.length;

  /* ---- render ---- */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-lg font-semibold text-slate-900">Phase Workflow</h2>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => advanceMut.mutate()}
            disabled={advanceMut.isPending}
            className="flex items-center gap-1.5 bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            <Play size={14} /> Advance Phase
          </button>
          <button
            onClick={() => setShowOverride((v) => !v)}
            className="flex items-center gap-1.5 border border-amber-300 text-amber-700 px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-amber-50 transition-colors"
          >
            <AlertTriangle size={14} /> Override
          </button>
          <button
            onClick={() => rollbackMut.mutate()}
            disabled={rollbackMut.isPending}
            className="flex items-center gap-1.5 border border-red-300 text-red-600 px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            <RotateCcw size={14} /> Rollback
          </button>
        </div>
      </div>

      {/* Override panel (collapsible) */}
      {showOverride && (
        <div className="bg-amber-50 rounded-xl border border-amber-200 p-4 animate-in slide-in-from-top-2">
          <h3 className="text-sm font-semibold text-amber-800 mb-2 flex items-center gap-1.5">
            <AlertTriangle size={14} /> Gate Override — Force Advance
          </h3>
          <div className="flex gap-2">
            <input
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Provide a reason for overriding the gate..."
              className="flex-1 border border-amber-300 rounded-lg px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-amber-400 focus:outline-none"
            />
            <button
              onClick={() => overrideMut.mutate()}
              disabled={!overrideReason.trim() || overrideMut.isPending}
              className="bg-amber-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 transition-colors whitespace-nowrap"
            >
              {overrideMut.isPending ? 'Overriding...' : 'Override & Advance'}
            </button>
          </div>
        </div>
      )}

      {/* Phase Timeline */}
      {phasesLoading ? (
        <div className="flex items-center justify-center py-12 text-slate-400">
          <div className="animate-spin rounded-full h-6 w-6 border-2 border-slate-300 border-t-blue-500" />
        </div>
      ) : phaseList.length === 0 ? (
        <div className="text-center py-12 text-slate-400 text-sm">No phases found for this project.</div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          {/* Horizontal timeline */}
          <div className="relative flex items-center justify-between overflow-x-auto pb-2 px-2">
            {phaseList.map((phase, i) => {
              const colors = statusColor(phase.status);
              const isSelected = selectedPhase === phase.id;
              const taskCount = phase.task_instances?.length ?? 0;
              const doneCount = phase.task_instances?.filter((t: any) => t.status === 'COMPLETED').length ?? 0;

              return (
                <div key={phase.id} className="flex items-center flex-1 min-w-0">
                  {/* Node */}
                  <button
                    onClick={() => setSelectedPhase(isSelected ? null : phase.id)}
                    className="flex flex-col items-center gap-1.5 group relative shrink-0"
                  >
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white ring-4 transition-all cursor-pointer ${colors.bg} ${
                        isSelected ? 'ring-blue-300 scale-110' : colors.ring
                      } group-hover:scale-105`}
                    >
                      {phase.status === 'COMPLETED' ? (
                        <CheckCircle2 size={18} />
                      ) : (
                        i + 1
                      )}
                    </div>
                    <span
                      className={`text-xs font-medium text-center max-w-[80px] truncate ${
                        isSelected ? 'text-blue-700' : colors.text
                      }`}
                    >
                      {phase.phase_name || `Phase ${(phase.order_number ?? i) + 1}`}
                    </span>
                    <StatusBadge status={phase.status} />
                    {taskCount > 0 && (
                      <MiniProgressBar completed={doneCount} total={taskCount} />
                    )}
                  </button>

                  {/* Connector line */}
                  {i < phaseList.length - 1 && (
                    <div className="flex-1 mx-1 min-w-[20px]">
                      <div
                        className={`h-0.5 w-full rounded-full ${
                          phase.status === 'COMPLETED' ? 'bg-green-400' : 'bg-slate-200'
                        }`}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Phase cards (vertical list) */}
      <div className="space-y-3">
        {phaseList.map((phase, i) => {
          const isSelected = selectedPhase === phase.id;
          const colors = statusColor(phase.status);
          const taskCount = phase.task_instances?.length ?? 0;
          const doneCount = phase.task_instances?.filter((t: any) => t.status === 'COMPLETED').length ?? 0;

          return (
            <div
              key={phase.id}
              onClick={() => setSelectedPhase(isSelected ? null : phase.id)}
              className={`bg-white rounded-xl border cursor-pointer transition-all ${
                isSelected
                  ? 'border-blue-400 shadow-md ring-1 ring-blue-100'
                  : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'
              }`}
            >
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-white shrink-0 ${colors.bg}`}
                    >
                      {phase.status === 'COMPLETED' ? (
                        <CheckCircle2 size={16} />
                      ) : (
                        (phase.order_number ?? i) + 1
                      )}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-900 truncate">
                          {phase.phase_name || `Phase ${(phase.order_number ?? i) + 1}`}
                        </span>
                        <StatusBadge status={phase.status} />
                      </div>
                      {/* Phase duration */}
                      {phase.started_at && (
                        <div className="flex items-center gap-3 mt-0.5 text-xs text-slate-400">
                          <span className="flex items-center gap-1">
                            <Calendar size={11} />
                            {formatDate(phase.started_at)}
                            {phase.completed_at ? ` - ${formatDate(phase.completed_at)}` : ' - ongoing'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock size={11} />
                            {durationLabel(phase.started_at, phase.completed_at)}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 ml-3">
                    {taskCount > 0 && <MiniProgressBar completed={doneCount} total={taskCount} />}

                    {phase.status === 'IN_PROGRESS' && (
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            gateMut.mutate(phase.id);
                          }}
                          disabled={gateMut.isPending}
                          className="flex items-center gap-1 text-xs bg-indigo-50 text-indigo-600 px-2.5 py-1 rounded-md hover:bg-indigo-100 disabled:opacity-50 transition-colors font-medium"
                        >
                          <Shield size={12} />
                          {gateMut.isPending ? 'Evaluating...' : 'Evaluate Gate'}
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            questionsMut.mutate(phase.id);
                          }}
                          disabled={questionsMut.isPending}
                          className="flex items-center gap-1 text-xs bg-purple-50 text-purple-600 px-2.5 py-1 rounded-md hover:bg-purple-100 disabled:opacity-50 transition-colors font-medium"
                        >
                          <Sparkles size={12} />
                          {questionsMut.isPending ? 'Generating...' : 'Generate AI Questions'}
                        </button>
                      </div>
                    )}

                    {isSelected ? (
                      <ChevronDown size={16} className="text-slate-400" />
                    ) : (
                      <ChevronRight size={16} className="text-slate-400" />
                    )}
                  </div>
                </div>

                {/* Inline gate results summary */}
                {phase.gate_results && !isSelected && (
                  <div className="mt-3 pl-12">
                    <GateEvaluationResults results={phase.gate_results} />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Phase Detail Panel */}
      {selectedPhase && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {detailLoading ? (
            <div className="flex items-center justify-center py-12 text-slate-400">
              <div className="animate-spin rounded-full h-6 w-6 border-2 border-slate-300 border-t-blue-500" />
            </div>
          ) : detail ? (
            <div className="divide-y divide-slate-100">
              {/* Detail header */}
              <div className="p-5">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-base font-semibold text-slate-900">
                    {detail.phase_name || 'Phase Detail'}
                  </h3>
                  <StatusBadge status={detail.status} />
                </div>

                {/* Description */}
                {detail.description && (
                  <p className="text-sm text-slate-600 mb-3">{detail.description}</p>
                )}

                {/* Metadata row */}
                <div className="flex items-center gap-4 flex-wrap text-xs text-slate-500">
                  {detail.order_number !== undefined && (
                    <span className="bg-slate-100 px-2 py-0.5 rounded">
                      Order: {detail.order_number + 1}
                    </span>
                  )}
                  {detail.started_at && (
                    <span className="flex items-center gap-1">
                      <Calendar size={11} /> Started: {formatDate(detail.started_at)}
                    </span>
                  )}
                  {detail.completed_at && (
                    <span className="flex items-center gap-1">
                      <CheckCircle2 size={11} /> Completed: {formatDate(detail.completed_at)}
                    </span>
                  )}
                  {detail.started_at && (
                    <span className="flex items-center gap-1">
                      <Clock size={11} /> Duration: {durationLabel(detail.started_at, detail.completed_at)}
                    </span>
                  )}
                </div>

                {/* Task summary bar */}
                {totalTasks > 0 && (
                  <div className="mt-4">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-slate-700">
                        Task Progress
                      </span>
                      <span className="text-sm text-slate-500">
                        {completedTasks}/{totalTasks} completed ({totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0}%)
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500 rounded-full transition-all duration-700"
                        style={{ width: `${totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Generate Questions button for active phase detail */}
                {detail.status === 'IN_PROGRESS' && (
                  <div className="mt-4">
                    <button
                      onClick={() => questionsMut.mutate(detail.id)}
                      disabled={questionsMut.isPending}
                      className="flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      <Sparkles size={15} />
                      {questionsMut.isPending ? 'Generating Questions...' : 'Generate AI Questions'}
                    </button>
                    {questionsMut.isSuccess && (
                      <p className="mt-1.5 text-xs text-green-600 flex items-center gap-1">
                        <CheckCircle2 size={12} /> Questions generated successfully
                      </p>
                    )}
                    {questionsMut.isError && (
                      <p className="mt-1.5 text-xs text-red-600 flex items-center gap-1">
                        <XCircle size={12} /> Failed to generate questions
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Gate criteria checklist */}
              {(detail.gate_criteria && detail.gate_criteria.length > 0) && (
                <div className="p-5">
                  <GateCriteriaChecklist
                    criteria={detail.gate_criteria}
                    results={detail.gate_results}
                  />
                </div>
              )}

              {/* Gate evaluation results */}
              {detail.gate_results && Object.keys(detail.gate_results).length > 0 && (
                <div className="p-5">
                  <GateEvaluationResults results={detail.gate_results} />
                </div>
              )}

              {/* Tasks grouped by classification */}
              {detailTasks.length > 0 && (
                <div className="p-5">
                  <h4 className="text-sm font-semibold text-slate-700 mb-3">Tasks by Classification</h4>
                  <TasksByClassification tasks={detailTasks} />
                </div>
              )}
            </div>
          ) : (
            <div className="p-5 text-sm text-slate-400 italic">Could not load phase details.</div>
          )}
        </div>
      )}
    </div>
  );
}
