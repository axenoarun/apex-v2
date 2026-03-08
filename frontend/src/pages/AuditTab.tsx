import { useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { listAuditLogs, getAuditSummary } from '../api/endpoints';

export default function AuditTab() {
  const { projectId } = useOutletContext<any>();

  const { data: logs, isLoading, error } = useQuery({
    queryKey: ['audit-logs', projectId],
    queryFn: () => listAuditLogs({ project_id: projectId, limit: '50' }).then((r) => r.data),
  });

  const { data: summary } = useQuery({
    queryKey: ['audit-summary', projectId],
    queryFn: () => getAuditSummary(projectId).then((r) => r.data),
  });

  if (isLoading) return <div className="text-slate-500 text-sm">Loading audit log...</div>;
  if (error) return <div className="text-slate-500 text-sm">Unable to load audit log (requires ARCHITECT role).</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Audit Log</h2>
        <span className="text-sm text-slate-500">{summary?.total_entries || 0} total entries</span>
      </div>

      {/* Summary */}
      {summary?.actions && Object.keys(summary.actions).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(summary.actions).map(([action, count]: any) => (
            <span key={action} className="bg-slate-100 text-slate-700 text-xs px-2 py-1 rounded">
              {action}: {count}
            </span>
          ))}
        </div>
      )}

      {/* Log entries */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Action</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Entity</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Actor</th>
              <th className="text-left px-4 py-2 text-slate-500 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {logs?.map((log: any) => (
              <tr key={log.id} className="border-b border-slate-100 last:border-0">
                <td className="px-4 py-2 font-medium text-slate-700">{log.action}</td>
                <td className="px-4 py-2 text-slate-600">{log.entity_type}</td>
                <td className="px-4 py-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${log.actor_type === 'SYSTEM' ? 'bg-purple-50 text-purple-600' : 'bg-blue-50 text-blue-600'}`}>
                    {log.actor_type}
                  </span>
                </td>
                <td className="px-4 py-2 text-xs text-slate-400">{new Date(log.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!logs || logs.length === 0) && <div className="text-center py-8 text-slate-400 text-sm">No audit entries.</div>}
      </div>
    </div>
  );
}
