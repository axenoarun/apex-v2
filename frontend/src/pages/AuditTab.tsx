import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listAuditLogs, getAuditSummary } from '../api/endpoints';
import { ScrollText, Filter, Clock, User, Cpu } from 'lucide-react';

export default function AuditTab() {
  const { projectId } = useOutletContext<any>();
  const [actionFilter, setActionFilter] = useState('ALL');
  const [actorFilter, setActorFilter] = useState('ALL');

  const { data: logs, isLoading, error } = useQuery({
    queryKey: ['audit-logs', projectId],
    queryFn: () => listAuditLogs({ project_id: projectId, limit: '100' }).then((r) => r.data),
  });

  const { data: summary } = useQuery({
    queryKey: ['audit-summary', projectId],
    queryFn: () => getAuditSummary(projectId).then((r) => r.data),
  });

  if (isLoading) return <div className="text-slate-500 text-sm">Loading audit log...</div>;
  if (error) return <div className="text-slate-500 text-sm">Unable to load audit log (requires ARCHITECT role).</div>;

  const actions = [...new Set(logs?.map((l: any) => l.action) || [])];
  const actorTypes = [...new Set(logs?.map((l: any) => l.actor_type) || [])];

  const filtered = logs?.filter((l: any) => {
    if (actionFilter !== 'ALL' && l.action !== actionFilter) return false;
    if (actorFilter !== 'ALL' && l.actor_type !== actorFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Audit Log</h2>
        <span className="text-sm text-slate-500">{summary?.total_entries || 0} total entries</span>
      </div>

      {/* Summary cards */}
      {summary?.actions && Object.keys(summary.actions).length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          {Object.entries(summary.actions).slice(0, 4).map(([action, count]: any) => (
            <div key={action} className="bg-white rounded-xl border border-slate-200 p-3 text-center">
              <div className="text-2xl font-bold text-slate-700">{count}</div>
              <div className="text-xs text-slate-500">{action}</div>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 bg-white rounded-xl border border-slate-200 p-3">
        <Filter size={14} className="text-slate-400" />
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Action:</span>
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="border border-slate-200 rounded px-2 py-1 text-xs"
          >
            <option value="ALL">All</option>
            {actions.map((a) => <option key={a as string} value={a as string}>{a as string}</option>)}
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">Actor:</span>
          <select
            value={actorFilter}
            onChange={(e) => setActorFilter(e.target.value)}
            className="border border-slate-200 rounded px-2 py-1 text-xs"
          >
            <option value="ALL">All</option>
            {actorTypes.map((a) => <option key={a as string} value={a as string}>{a as string}</option>)}
          </select>
        </div>
        <span className="text-xs text-slate-400 ml-auto">{filtered?.length || 0} entries shown</span>
      </div>

      {/* Log entries */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Action</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Entity</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Details</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Actor</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {filtered?.map((log: any) => (
              <tr key={log.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                <td className="px-4 py-2">
                  <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                    log.action === 'CREATE' ? 'bg-green-50 text-green-600'
                    : log.action === 'UPDATE' ? 'bg-blue-50 text-blue-600'
                    : log.action === 'DELETE' ? 'bg-red-50 text-red-600'
                    : 'bg-slate-50 text-slate-600'
                  }`}>
                    {log.action}
                  </span>
                </td>
                <td className="px-4 py-2 text-slate-600 text-xs">{log.entity_type}</td>
                <td className="px-4 py-2 text-xs text-slate-500 max-w-xs truncate">
                  {log.entity_id?.slice(0, 8)}...
                </td>
                <td className="px-4 py-2">
                  <span className={`inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded ${
                    log.actor_type === 'SYSTEM' ? 'bg-purple-50 text-purple-600' : 'bg-blue-50 text-blue-600'
                  }`}>
                    {log.actor_type === 'SYSTEM' ? <Cpu size={10} /> : <User size={10} />}
                    {log.actor_type}
                  </span>
                </td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-1 text-xs text-slate-400">
                    <Clock size={10} />
                    {new Date(log.created_at).toLocaleString()}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!filtered || filtered.length === 0) && <div className="text-center py-8 text-slate-400 text-sm">No audit entries.</div>}
      </div>
    </div>
  );
}
