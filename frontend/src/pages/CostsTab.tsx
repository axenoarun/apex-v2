import { useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { getProjectCosts } from '../api/endpoints';
import { DollarSign, Cpu, RefreshCw } from 'lucide-react';

export default function CostsTab() {
  const { projectId } = useOutletContext<any>();

  const { data: costs, isLoading, error } = useQuery({
    queryKey: ['costs', projectId],
    queryFn: () => getProjectCosts(projectId).then((r) => r.data),
  });

  if (isLoading) return <div className="text-slate-500 text-sm">Loading costs...</div>;
  if (error) return <div className="text-slate-500 text-sm">Unable to load cost data (requires ARCHITECT role).</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-slate-900">Cost Tracking</h2>

      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={18} className="text-green-600" />
            <span className="text-sm text-slate-500">Total Cost</span>
          </div>
          <div className="text-3xl font-bold text-slate-900">${costs?.total_cost_usd?.toFixed(4) || '0.00'}</div>
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
    </div>
  );
}
