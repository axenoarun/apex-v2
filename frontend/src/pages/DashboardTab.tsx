import { useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  listTasks,
  listProjectPhases,
  getQuestionStats,
  getEvalSummary,
  getProjectCosts,
  listAuditLogs,
} from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import {
  Activity,
  BarChart3,
  Brain,
  DollarSign,
  CheckCircle2,
  Clock,
  FileText,
  Shield,
  Bot,
  HelpCircle,
  AlertTriangle,
  Zap,
  Users,
  TrendingUp,
} from 'lucide-react';

export default function DashboardTab() {
  const { projectId } = useOutletContext<any>();

  const { data: tasks } = useQuery({
    queryKey: ['tasks', projectId],
    queryFn: () => listTasks({ project_id: projectId }).then((r) => r.data),
  });

  const { data: phases } = useQuery({
    queryKey: ['phases', projectId],
    queryFn: () => listProjectPhases(projectId).then((r) => r.data),
  });

  const { data: qStats } = useQuery({
    queryKey: ['question-stats', projectId],
    queryFn: () => getQuestionStats(projectId).then((r) => r.data),
  });

  const { data: evalSummary } = useQuery({
    queryKey: ['eval-summary', projectId],
    queryFn: () => getEvalSummary(projectId).then((r) => r.data),
  });

  const { data: costs } = useQuery({
    queryKey: ['project-costs', projectId],
    queryFn: () => getProjectCosts(projectId).then((r) => r.data),
  });

  const { data: auditLogs } = useQuery({
    queryKey: ['audit-logs', projectId],
    queryFn: () => listAuditLogs({ project_id: projectId, limit: '5' }).then((r) => r.data),
  });

  // --- Derived task stats ---
  const totalTasks = tasks?.length || 0;
  const completedTasks = tasks?.filter((t: any) => t.status === 'COMPLETED').length || 0;
  const inProgressTasks = tasks?.filter((t: any) => t.status === 'IN_PROGRESS').length || 0;
  const notStartedTasks = tasks?.filter((t: any) => t.status === 'NOT_STARTED').length || 0;
  const blockedTasks = tasks?.filter((t: any) => t.status === 'BLOCKED').length || 0;
  const aiTasks = tasks?.filter((t: any) => t.classification === 'AI').length || 0;
  const manualTasks = tasks?.filter((t: any) => t.classification === 'MANUAL').length || 0;
  const hybridTasks = tasks?.filter((t: any) => t.classification === 'HYBRID').length || 0;

  // --- Phase stats ---
  const phaseList: any[] = phases || [];
  const completedPhases = phaseList.filter((p) => p.status === 'COMPLETED').length;
  const inProgressPhases = phaseList.filter((p) => p.status === 'IN_PROGRESS').length;
  const notStartedPhases = phaseList.filter((p) => p.status === 'NOT_STARTED').length;
  const totalPhases = phaseList.length;
  const activePhase = phaseList.find((p: any) => p.status === 'IN_PROGRESS');

  // --- Eval stats ---
  const totalEvals = evalSummary?.total_evals || 0;
  const avgScore = evalSummary?.avg_score != null ? Number(evalSummary.avg_score).toFixed(2) : '---';
  const passedEvals = evalSummary?.passed || 0;
  const failedEvals = evalSummary?.failed || 0;
  const passRate = totalEvals > 0 ? Math.round((passedEvals / totalEvals) * 100) : 0;

  // --- Question stats ---
  const totalQuestions = qStats?.total || 0;
  const answeredQuestions = qStats?.answered || 0;
  const pendingQuestions = totalQuestions - answeredQuestions;
  const questionCompletionPct = totalQuestions > 0 ? Math.round((answeredQuestions / totalQuestions) * 100) : 0;

  // --- Cost stats ---
  const totalCost = costs?.total_cost != null ? Number(costs.total_cost).toFixed(2) : '0.00';
  const totalTokens = costs?.total_tokens || 0;
  const costBreakdown: any[] = costs?.breakdown || [];

  // --- Audit logs ---
  const logs: any[] = Array.isArray(auditLogs) ? auditLogs : [];

  // Format relative time
  function timeAgo(dateStr: string): string {
    const now = new Date();
    const date = new Date(dateStr);
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    if (seconds < 60) return 'just now';
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }

  return (
    <div className="space-y-6">
      {/* ========== PHASE PROGRESS BAR ========== */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={18} className="text-slate-500" />
          <h3 className="font-semibold text-slate-900">Phase Progress</h3>
          <span className="ml-auto text-sm text-slate-500">
            {completedPhases}/{totalPhases} completed
          </span>
        </div>
        {totalPhases > 0 ? (
          <>
            <div className="flex w-full h-8 rounded-lg overflow-hidden border border-slate-200">
              {phaseList.map((phase: any, i: number) => {
                const widthPct = 100 / totalPhases;
                const bgColor =
                  phase.status === 'COMPLETED'
                    ? 'bg-green-500'
                    : phase.status === 'IN_PROGRESS'
                      ? 'bg-blue-500'
                      : 'bg-slate-200';
                const textColor =
                  phase.status === 'NOT_STARTED' ? 'text-slate-500' : 'text-white';
                return (
                  <div
                    key={phase.id}
                    className={`${bgColor} ${textColor} flex items-center justify-center text-xs font-medium relative`}
                    style={{ width: `${widthPct}%` }}
                    title={`Phase ${i + 1}: ${phase.status}`}
                  >
                    {i + 1}
                    {i < totalPhases - 1 && (
                      <div className="absolute right-0 top-0 bottom-0 w-px bg-white/40" />
                    )}
                  </div>
                );
              })}
            </div>
            <div className="flex w-full mt-1.5">
              {phaseList.map((phase: any, i: number) => {
                const widthPct = 100 / totalPhases;
                return (
                  <div
                    key={phase.id}
                    className="text-center text-[10px] text-slate-500 truncate px-0.5"
                    style={{ width: `${widthPct}%` }}
                  >
                    {phase.phase_name || phase.name || `Phase ${i + 1}`}
                  </div>
                );
              })}
            </div>
            <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-green-500 inline-block" /> Completed
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-blue-500 inline-block" /> In Progress
              </span>
              <span className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm bg-slate-200 inline-block" /> Not Started
              </span>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-400">No phases found.</p>
        )}
      </div>

      {/* ========== TASK BREAKDOWN ========== */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 mb-4">
          <FileText size={18} className="text-slate-500" />
          <h3 className="font-semibold text-slate-900">Task Breakdown</h3>
          <span className="ml-auto text-sm text-slate-500">{totalTasks} total</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {/* By classification */}
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-3">
              By Classification
            </p>
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-lg bg-purple-50 border border-purple-100 p-3 text-center">
                <Bot size={16} className="text-purple-600 mx-auto mb-1" />
                <p className="text-lg font-bold text-purple-700">{aiTasks}</p>
                <p className="text-[11px] text-purple-500">AI</p>
              </div>
              <div className="rounded-lg bg-amber-50 border border-amber-100 p-3 text-center">
                <Users size={16} className="text-amber-600 mx-auto mb-1" />
                <p className="text-lg font-bold text-amber-700">{manualTasks}</p>
                <p className="text-[11px] text-amber-500">Manual</p>
              </div>
              <div className="rounded-lg bg-cyan-50 border border-cyan-100 p-3 text-center">
                <Zap size={16} className="text-cyan-600 mx-auto mb-1" />
                <p className="text-lg font-bold text-cyan-700">{hybridTasks}</p>
                <p className="text-[11px] text-cyan-500">Hybrid</p>
              </div>
            </div>
          </div>
          {/* By status */}
          <div>
            <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-3">
              By Status
            </p>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-green-50 border border-green-100 p-3 flex items-center gap-2">
                <CheckCircle2 size={16} className="text-green-600 shrink-0" />
                <div>
                  <p className="text-lg font-bold text-green-700 leading-none">{completedTasks}</p>
                  <p className="text-[11px] text-green-500">Completed</p>
                </div>
              </div>
              <div className="rounded-lg bg-blue-50 border border-blue-100 p-3 flex items-center gap-2">
                <Clock size={16} className="text-blue-600 shrink-0" />
                <div>
                  <p className="text-lg font-bold text-blue-700 leading-none">{inProgressTasks}</p>
                  <p className="text-[11px] text-blue-500">In Progress</p>
                </div>
              </div>
              <div className="rounded-lg bg-slate-50 border border-slate-200 p-3 flex items-center gap-2">
                <Clock size={16} className="text-slate-400 shrink-0" />
                <div>
                  <p className="text-lg font-bold text-slate-600 leading-none">{notStartedTasks}</p>
                  <p className="text-[11px] text-slate-400">Not Started</p>
                </div>
              </div>
              <div className="rounded-lg bg-red-50 border border-red-100 p-3 flex items-center gap-2">
                <AlertTriangle size={16} className="text-red-600 shrink-0" />
                <div>
                  <p className="text-lg font-bold text-red-700 leading-none">{blockedTasks}</p>
                  <p className="text-[11px] text-red-500">Blocked</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        {/* Task completion bar */}
        {totalTasks > 0 && (
          <div className="mt-4">
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Overall completion</span>
              <span>{totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0}%</span>
            </div>
            <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-green-500 transition-all duration-500"
                style={{ width: `${totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ========== MIDDLE ROW: AI Quality + Cost Summary ========== */}
      <div className="grid grid-cols-2 gap-6">
        {/* AI Quality Metrics */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={18} className="text-slate-500" />
            <h3 className="font-semibold text-slate-900">AI Quality Metrics</h3>
          </div>
          <div className="flex items-start gap-6">
            {/* Big avg score */}
            <div className="text-center">
              <p className="text-4xl font-extrabold text-slate-900 leading-none">{avgScore}</p>
              <p className="text-xs text-slate-500 mt-1">Avg Score</p>
            </div>
            {/* Stats column */}
            <div className="flex-1 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Pass Rate</span>
                <span className="text-sm font-semibold text-green-700">{passRate}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full rounded-full bg-green-500 transition-all duration-500"
                  style={{ width: `${passRate}%` }}
                />
              </div>
              <div className="flex gap-4 pt-1">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
                  <span className="text-xs text-slate-600">
                    {passedEvals} passed
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                  <span className="text-xs text-slate-600">
                    {failedEvals} failed
                  </span>
                </div>
              </div>
              <div className="flex items-center justify-between text-sm text-slate-500 pt-1">
                <span>Total Evaluations</span>
                <span className="font-semibold text-slate-700">{totalEvals}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Cost Summary */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <DollarSign size={18} className="text-slate-500" />
            <h3 className="font-semibold text-slate-900">Cost Summary</h3>
          </div>
          <div className="flex items-start gap-6">
            <div className="text-center">
              <p className="text-3xl font-extrabold text-slate-900 leading-none">${totalCost}</p>
              <p className="text-xs text-slate-500 mt-1">Total Cost</p>
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-600">Tokens Used</span>
                <span className="font-semibold text-slate-700">
                  {totalTokens > 1000
                    ? `${(totalTokens / 1000).toFixed(1)}k`
                    : totalTokens}
                </span>
              </div>
              {costBreakdown.length > 0 && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-[11px] text-slate-400 uppercase tracking-wide font-medium">
                    Breakdown
                  </p>
                  {costBreakdown.slice(0, 4).map((item: any, i: number) => {
                    const label = item.model || item.category || item.agent || `Item ${i + 1}`;
                    const amount = Number(item.cost || item.amount || 0).toFixed(2);
                    return (
                      <div key={i} className="flex justify-between text-xs">
                        <span className="text-slate-500 truncate max-w-[140px]">{label}</span>
                        <span className="text-slate-700 font-medium">${amount}</span>
                      </div>
                    );
                  })}
                </div>
              )}
              {costBreakdown.length === 0 && (
                <p className="text-xs text-slate-400 mt-2">No breakdown available.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ========== BOTTOM ROW: Questions + Gate Readiness + Recent Activity ========== */}
      <div className="grid grid-cols-3 gap-6">
        {/* Question Stats */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <HelpCircle size={18} className="text-slate-500" />
            <h3 className="font-semibold text-slate-900">Questions</h3>
          </div>
          <div className="flex items-center gap-4 mb-4">
            {/* Circular-style percentage using a ring approximation */}
            <div className="relative w-16 h-16 shrink-0">
              <svg viewBox="0 0 36 36" className="w-16 h-16 -rotate-90">
                <circle
                  cx="18"
                  cy="18"
                  r="15.91"
                  fill="none"
                  stroke="#e2e8f0"
                  strokeWidth="3"
                />
                <circle
                  cx="18"
                  cy="18"
                  r="15.91"
                  fill="none"
                  stroke="#22c55e"
                  strokeWidth="3"
                  strokeDasharray={`${questionCompletionPct} ${100 - questionCompletionPct}`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-sm font-bold text-slate-900">{questionCompletionPct}%</span>
              </div>
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-green-500" />
                <span className="text-xs text-slate-600">{answeredQuestions} answered</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                <span className="text-xs text-slate-600">{pendingQuestions} pending</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-300" />
                <span className="text-xs text-slate-600">{totalQuestions} total</span>
              </div>
            </div>
          </div>
        </div>

        {/* Gate Readiness */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={18} className="text-slate-500" />
            <h3 className="font-semibold text-slate-900">Gate Readiness</h3>
          </div>
          {activePhase ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-600">Active Phase</span>
                <StatusBadge status={activePhase.status} />
              </div>
              <p className="text-sm font-medium text-slate-800">
                {activePhase.phase_name || activePhase.name || 'Current Phase'}
              </p>
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">Gate Status</span>
                <span
                  className={`font-semibold ${
                    activePhase.gate_status === 'PASSED'
                      ? 'text-green-600'
                      : activePhase.gate_status === 'FAILED'
                        ? 'text-red-600'
                        : 'text-amber-600'
                  }`}
                >
                  {activePhase.gate_status || 'NOT EVALUATED'}
                </span>
              </div>
              {activePhase.gate_criteria && (
                <div className="mt-2">
                  <p className="text-[11px] text-slate-400 uppercase tracking-wide mb-1 font-medium">
                    Criteria
                  </p>
                  <ul className="space-y-1">
                    {(Array.isArray(activePhase.gate_criteria)
                      ? activePhase.gate_criteria
                      : []
                    ).map((criterion: any, i: number) => (
                      <li key={i} className="flex items-center gap-1.5 text-xs text-slate-600">
                        {criterion.met ? (
                          <CheckCircle2 size={12} className="text-green-500 shrink-0" />
                        ) : (
                          <Clock size={12} className="text-slate-400 shrink-0" />
                        )}
                        <span className="truncate">{criterion.name || criterion.description || `Criterion ${i + 1}`}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {!activePhase.gate_criteria && (
                <p className="text-xs text-slate-400">No gate criteria defined.</p>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-4 text-slate-400">
              <Shield size={24} className="mb-2" />
              <p className="text-sm">No active phase</p>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={18} className="text-slate-500" />
            <h3 className="font-semibold text-slate-900">Recent Activity</h3>
          </div>
          {logs.length > 0 ? (
            <div className="space-y-3">
              {logs.slice(0, 5).map((log: any, i: number) => (
                <div key={log.id || i} className="flex items-start gap-2.5">
                  <div className="mt-0.5 w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                    <TrendingUp size={12} className="text-slate-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-700 truncate">
                      <span className="font-medium">{log.action || 'Action'}</span>
                      {log.entity_type && (
                        <span className="text-slate-400"> on {log.entity_type}</span>
                      )}
                    </p>
                    <p className="text-[11px] text-slate-400">
                      {log.created_at ? timeAgo(log.created_at) : log.timestamp ? timeAgo(log.timestamp) : ''}
                      {log.user_email && (
                        <span> by {log.user_email}</span>
                      )}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-4 text-slate-400">
              <Activity size={24} className="mb-2" />
              <p className="text-sm">No recent activity</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
