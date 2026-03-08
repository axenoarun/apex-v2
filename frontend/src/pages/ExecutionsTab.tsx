import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listExecutions, getExecution, resumeExecution } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import {
  Cpu,
  ChevronDown,
  ChevronRight,
  Play,
  Clock,
  DollarSign,
  Zap,
  Layers,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';

const STATUS_FILTERS = ['ALL', 'PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'PAUSED'] as const;

function formatDuration(startStr: string, endStr?: string | null): string {
  const start = new Date(startStr).getTime();
  const end = endStr ? new Date(endStr).getTime() : Date.now();
  const diffMs = end - start;
  if (diffMs < 0) return '--';
  const seconds = Math.floor(diffMs / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainSec = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainSec}s`;
  const hours = Math.floor(minutes / 60);
  const remainMin = minutes % 60;
  return `${hours}h ${remainMin}m`;
}

export default function ExecutionsTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: executions, isLoading } = useQuery({
    queryKey: ['executions', projectId, statusFilter],
    queryFn: () => {
      const params: Record<string, string> = { project_id: projectId };
      if (statusFilter !== 'ALL') params.status = statusFilter;
      return listExecutions(params).then((r) => r.data);
    },
  });

  const { data: executionDetail } = useQuery({
    queryKey: ['execution-detail', expandedId],
    queryFn: () => getExecution(expandedId!).then((r) => r.data),
    enabled: !!expandedId,
  });

  const resumeMut = useMutation({
    mutationFn: (executionId: string) => resumeExecution(executionId, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['executions'] });
      qc.invalidateQueries({ queryKey: ['execution-detail'] });
    },
  });

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  if (isLoading) return <div className="text-slate-500 text-sm">Loading executions...</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Agent Executions</h2>
        <span className="text-sm text-slate-400">{executions?.length || 0} executions</span>
      </div>

      {/* Status filters */}
      <div className="flex gap-1 flex-wrap">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              statusFilter === s ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {s.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Execution list */}
      <div className="space-y-2">
        {executions?.map((exec: any) => {
          const isExpanded = expandedId === exec.id;
          const detail = isExpanded ? executionDetail : null;

          return (
            <div
              key={exec.id}
              className="bg-white rounded-xl border border-slate-200 overflow-hidden"
            >
              {/* Row header */}
              <div
                onClick={() => toggleExpand(exec.id)}
                className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-50 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  {isExpanded ? (
                    <ChevronDown size={16} className="text-slate-400 flex-shrink-0" />
                  ) : (
                    <ChevronRight size={16} className="text-slate-400 flex-shrink-0" />
                  )}
                  <Cpu size={16} className="text-purple-500 flex-shrink-0" />
                  <span className="text-sm font-medium text-slate-800 font-mono truncate max-w-[160px]">
                    {exec.agent_definition_id
                      ? exec.agent_definition_id.slice(0, 12) + '...'
                      : exec.id.slice(0, 12) + '...'}
                  </span>
                  <StatusBadge status={exec.status} />
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-500 flex-shrink-0">
                  {/* Confidence */}
                  {exec.confidence_score != null && (
                    <div className="flex items-center gap-1" title="Confidence">
                      <CheckCircle2 size={12} className="text-green-500" />
                      <span>{(exec.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                  )}

                  {/* Tokens */}
                  <div className="flex items-center gap-1" title="Tokens (in/out)">
                    <Zap size={12} className="text-amber-500" />
                    <span>
                      {(exec.tokens_input ?? 0).toLocaleString()}/{(exec.tokens_output ?? 0).toLocaleString()}
                    </span>
                  </div>

                  {/* Cost */}
                  {exec.cost_usd != null && (
                    <div className="flex items-center gap-1" title="Cost (USD)">
                      <DollarSign size={12} className="text-green-600" />
                      <span>${exec.cost_usd.toFixed(4)}</span>
                    </div>
                  )}

                  {/* Duration */}
                  {exec.created_at && (
                    <div className="flex items-center gap-1" title="Duration">
                      <Clock size={12} className="text-blue-500" />
                      <span>{formatDuration(exec.created_at, exec.completed_at)}</span>
                    </div>
                  )}

                  {/* Timestamps */}
                  <span className="text-slate-400 w-[130px] text-right">
                    {new Date(exec.created_at).toLocaleString()}
                  </span>

                  {/* Resume button for PAUSED */}
                  {exec.status === 'PAUSED' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        resumeMut.mutate(exec.id);
                      }}
                      disabled={resumeMut.isPending}
                      className="flex items-center gap-1 bg-orange-50 text-orange-600 px-2.5 py-1 rounded-lg hover:bg-orange-100 transition-colors ml-1"
                    >
                      <Play size={12} />
                      <span>Resume</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="border-t border-slate-100 bg-slate-50 p-4 space-y-4">
                  {!detail ? (
                    <div className="text-sm text-slate-400">Loading details...</div>
                  ) : (
                    <>
                      {/* Timestamps */}
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-slate-500">Created:</span>{' '}
                          <span className="text-slate-700">
                            {detail.created_at ? new Date(detail.created_at).toLocaleString() : '--'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">Completed:</span>{' '}
                          <span className="text-slate-700">
                            {detail.completed_at ? new Date(detail.completed_at).toLocaleString() : '--'}
                          </span>
                        </div>
                      </div>

                      {/* Input context */}
                      {detail.input_context && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1 flex items-center gap-1">
                            <Layers size={12} /> Input Context
                          </h4>
                          <pre className="bg-white border border-slate-200 rounded-lg p-3 text-xs text-slate-700 overflow-x-auto max-h-48 overflow-y-auto">
                            {JSON.stringify(detail.input_context, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Output */}
                      {detail.output && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1 flex items-center gap-1">
                            <CheckCircle2 size={12} /> Output
                          </h4>
                          <pre className="bg-white border border-slate-200 rounded-lg p-3 text-xs text-slate-700 overflow-x-auto max-h-48 overflow-y-auto">
                            {JSON.stringify(detail.output, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Eval scores */}
                      {detail.eval_scores && Object.keys(detail.eval_scores).length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">
                            Eval Scores
                          </h4>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(detail.eval_scores).map(([key, value]: [string, any]) => (
                              <div
                                key={key}
                                className="bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs"
                              >
                                <span className="text-slate-500">{key}:</span>{' '}
                                <span className="font-medium text-slate-800">
                                  {typeof value === 'number' ? value.toFixed(2) : String(value)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Tools called */}
                      {detail.tools_called && detail.tools_called.length > 0 && (
                        <div>
                          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1 flex items-center gap-1">
                            <Zap size={12} /> Tools Called
                          </h4>
                          <div className="flex flex-wrap gap-1.5">
                            {detail.tools_called.map((tool: string, i: number) => (
                              <span
                                key={i}
                                className="inline-block bg-purple-50 text-purple-700 px-2 py-0.5 rounded text-xs font-mono"
                              >
                                {tool}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Error info for FAILED */}
                      {detail.status === 'FAILED' && detail.error && (
                        <div>
                          <h4 className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-1 flex items-center gap-1">
                            <AlertCircle size={12} /> Error
                          </h4>
                          <pre className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700 overflow-x-auto max-h-32 overflow-y-auto">
                            {typeof detail.error === 'string'
                              ? detail.error
                              : JSON.stringify(detail.error, null, 2)}
                          </pre>
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empty state */}
      {(!executions || executions.length === 0) && (
        <div className="text-center py-12">
          <Cpu size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-400 text-sm">
            {statusFilter !== 'ALL'
              ? 'No executions match this status filter.'
              : 'No agent executions yet. Executions appear when AI tasks are run.'}
          </p>
        </div>
      )}
    </div>
  );
}
