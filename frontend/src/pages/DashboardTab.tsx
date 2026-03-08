import { useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listTasks, listProjectPhases, getQuestionStats, getEvalSummary } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { CheckCircle2, Clock, AlertTriangle, Bot } from 'lucide-react';

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

  const totalTasks = tasks?.length || 0;
  const completedTasks = tasks?.filter((t: any) => t.status === 'COMPLETED').length || 0;
  const inProgress = tasks?.filter((t: any) => t.status === 'IN_PROGRESS').length || 0;
  const aiTasks = tasks?.filter((t: any) => t.classification === 'AI').length || 0;
  const cards = [
    { label: 'Completed', value: `${completedTasks}/${totalTasks}`, icon: CheckCircle2, color: 'text-green-600 bg-green-50' },
    { label: 'In Progress', value: inProgress, icon: Clock, color: 'text-blue-600 bg-blue-50' },
    { label: 'AI Tasks', value: aiTasks, icon: Bot, color: 'text-purple-600 bg-purple-50' },
    { label: 'Questions', value: `${qStats?.answered || 0}/${qStats?.total || 0}`, icon: AlertTriangle, color: 'text-amber-600 bg-amber-50' },
  ];

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-4 gap-4">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-500">{label}</span>
              <div className={`p-1.5 rounded-lg ${color}`}>
                <Icon size={16} />
              </div>
            </div>
            <div className="text-2xl font-bold text-slate-900">{value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Phase progress */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-900 mb-4">Phase Progress</h3>
          <div className="space-y-3">
            {phases?.map((phase: any, i: number) => (
              <div key={phase.id} className="flex items-center gap-3">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  phase.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                  phase.status === 'IN_PROGRESS' ? 'bg-blue-100 text-blue-700' :
                  'bg-slate-100 text-slate-500'
                }`}>
                  {i + 1}
                </div>
                <div className="flex-1">
                  <span className="text-sm text-slate-700">Phase {i + 1}</span>
                </div>
                <StatusBadge status={phase.status} />
              </div>
            ))}
          </div>
        </div>

        {/* Eval summary */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-900 mb-4">AI Quality</h3>
          <div className="space-y-4">
            <div>
              <span className="text-sm text-slate-500">Evaluations Run</span>
              <p className="text-2xl font-bold">{evalSummary?.total_evals || 0}</p>
            </div>
            <div>
              <span className="text-sm text-slate-500">Avg Score</span>
              <p className="text-2xl font-bold">{evalSummary?.avg_score || '—'}</p>
            </div>
            <div className="flex gap-4">
              <div>
                <span className="text-sm text-green-600">Passed</span>
                <p className="text-lg font-bold text-green-700">{evalSummary?.passed || 0}</p>
              </div>
              <div>
                <span className="text-sm text-red-600">Failed</span>
                <p className="text-lg font-bold text-red-700">{evalSummary?.failed || 0}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
