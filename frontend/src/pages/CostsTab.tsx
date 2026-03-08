import { useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getProjectCosts, listExecutions } from '../api/endpoints';
import { DollarSign, Cpu, RefreshCw, TrendingUp, Zap, BarChart3 } from 'lucide-react';

export default function CostsTab() {
  const { projectId } = useOutletContext<any>();

  const { data: costs, isLoading, error } = useQuery({
    queryKey: ['costs', projectId],
    queryFn: () => getProjectCosts(projectId).then((r) => r.data),
  });

  const { data: executions } = useQuery({
    queryKey: ['executions-cost', projectId],
    queryFn: () => listExecutions({ project_id: projectId }).then((r) => r.data),
  });

  if (isLoading) return <div className="text-slate-500 text-sm">Loading costs...</div>;
  if (error) return <div className="text-slate-500 text-sm">Unable to load cost data (requires ARCHITECT role).</div>;

  // Calculate per-execution cost breakdown
  const execCosts = executions?.filter((e: any) => e.cost_usd > 0) || [];
  const avgCostPerExec = execCosts.length > 0
    ? execCosts.reduce((sum: number, e: any) => sum + (parseFloat(e.cost_usd) || 0), 0) / execCosts.length
    : 0;
  const totalExecCost = execCosts.reduce((sum: number, e: any) => sum + (parseFloat(e.cost_usd) || 0), 0);
  const reworkPct = costs?.total_entries > 0 ? Math.round((costs.rework_count / costs.total_entries) * 100) : 0;
  const evalPct = costs?.total_entries > 0 ? Math.round((costs.eval_count / costs.total_entries) * 100) : 0;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-slate-900">Cost Tracking</h2>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={18} className="text-green-600" />
            <span className="text-sm text-slate-500">Total Cost</span>
          </div>
          <div className="text-3xl font-bold text-slate-900">${costs?.total_cost_usd?.toFixed(4) || '0.00'}</div>
          <div className="text-xs text-slate-400 mt-1">
            Avg per execution: ${avgCostPerExec.toFixed(4)}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <Cpu size={18} className="text-blue-600" />
            <span className="text-sm text-slate-500">Total Tokens</span>
          </div>
          <div className="text-3xl font-bold text-slate-900">
            {((costs?.total_tokens_input || 0) + (costs?.total_tokens_output || 0)).toLocaleString()}
          </div>
          <div className="text-xs text-slate-400 mt-1">
            In: {costs?.total_tokens_input?.toLocaleString() || 0} | Out: {costs?.total_tokens_output?.toLocaleString() || 0}
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <RefreshCw size={18} className="text-orange-600" />
            <span className="text-sm text-slate-500">Entries</span>
          </div>
          <div className="text-3xl font-bold text-slate-900">{costs?.total_entries || 0}</div>
          <div className="text-xs text-slate-400 mt-1">
            Rework: {costs?.rework_count || 0} | Eval: {costs?.eval_count || 0}
          </div>
        </div>
      </div>

      {/* Cost breakdown visualization */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={16} className="text-slate-600" />
          <span className="text-sm font-medium text-slate-900">Cost Breakdown</span>
        </div>
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>AI Execution</span>
              <span>${totalExecCost.toFixed(4)}</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div
                className="bg-blue-500 h-2 rounded-full"
                style={{ width: costs?.total_cost_usd > 0 ? `${Math.min(100, (totalExecCost / costs.total_cost_usd) * 100)}%` : '0%' }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Rework ({reworkPct}% of entries)</span>
              <span>{costs?.rework_count || 0} entries</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${reworkPct}%` }} />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Evaluations ({evalPct}% of entries)</span>
              <span>{costs?.eval_count || 0} entries</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2">
              <div className="bg-purple-500 h-2 rounded-full" style={{ width: `${evalPct}%` }} />
            </div>
          </div>
        </div>
      </div>

      {/* Token efficiency */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={16} className="text-green-600" />
            <span className="text-sm font-medium text-slate-900">Token Efficiency</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Input tokens</span>
              <span className="font-medium">{costs?.total_tokens_input?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Output tokens</span>
              <span className="font-medium">{costs?.total_tokens_output?.toLocaleString() || 0}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">I/O Ratio</span>
              <span className="font-medium">
                {costs?.total_tokens_output > 0
                  ? (costs.total_tokens_input / costs.total_tokens_output).toFixed(1) + ':1'
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-3">
            <Zap size={16} className="text-amber-600" />
            <span className="text-sm font-medium text-slate-900">Execution Summary</span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Total executions</span>
              <span className="font-medium">{executions?.length || 0}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Completed</span>
              <span className="font-medium">{executions?.filter((e: any) => e.status === 'COMPLETED').length || 0}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Failed</span>
              <span className="font-medium text-red-600">{executions?.filter((e: any) => e.status === 'FAILED').length || 0}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">Avg cost/execution</span>
              <span className="font-medium">${avgCostPerExec.toFixed(4)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
