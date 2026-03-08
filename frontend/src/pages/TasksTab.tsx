import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listTasks,
  getTask,
  updateTask,
  completeTask,
  executeAITask,
  resumeExecution,
  listExecutions,
  assignTask,
  listUsers,
} from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import {
  Bot,
  User,
  ArrowLeftRight,
  CheckCircle2,
  Play,
  RefreshCw,
  GitBranch,
  Send,
  ChevronDown,
  Zap,
  DollarSign,
  Shield,
  Clock,
  FileText,
  AlertCircle,
  Loader2,
} from 'lucide-react';

const STATUS_FILTERS = [
  'ALL',
  'NOT_STARTED',
  'IN_PROGRESS',
  'AI_PROCESSING',
  'AI_PAUSED_NEEDS_INPUT',
  'WAITING_INPUT',
  'IN_REVIEW',
  'COMPLETED',
  'BLOCKED',
];

export default function TasksTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [filter, setFilter] = useState('ALL');
  const [selectedTask, setSelectedTask] = useState<string | null>(null);
  const [resumeInput, setResumeInput] = useState('');
  const [showAssignDropdown, setShowAssignDropdown] = useState(false);

  // --- Queries ---

  const { data: tasks } = useQuery({
    queryKey: ['tasks', projectId, filter],
    queryFn: () => {
      const params: Record<string, string> = { project_id: projectId };
      if (filter !== 'ALL') params.status = filter;
      return listTasks(params).then((r) => r.data);
    },
  });

  const { data: taskDetail } = useQuery({
    queryKey: ['task-detail', selectedTask],
    queryFn: () => getTask(selectedTask!).then((r) => r.data),
    enabled: !!selectedTask,
  });

  const { data: executions } = useQuery({
    queryKey: ['executions', selectedTask],
    queryFn: () =>
      listExecutions({ task_instance_id: selectedTask!, project_id: projectId }).then((r) => r.data),
    enabled: !!selectedTask,
  });

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: () => listUsers().then((r) => r.data),
  });

  // --- Mutations ---

  const startMut = useMutation({
    mutationFn: (id: string) => updateTask(id, { status: 'IN_PROGRESS' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['task-detail'] });
    },
  });

  const completeMut = useMutation({
    mutationFn: (id: string) => completeTask(id, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['task-detail'] });
      setSelectedTask(null);
    },
  });

  const executeAIMut = useMutation({
    mutationFn: (id: string) => executeAITask(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['task-detail'] });
      qc.invalidateQueries({ queryKey: ['executions'] });
    },
  });

  const resumeMut = useMutation({
    mutationFn: ({ executionId, input }: { executionId: string; input: string }) =>
      resumeExecution(executionId, { user_input: input }),
    onSuccess: () => {
      setResumeInput('');
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['task-detail'] });
      qc.invalidateQueries({ queryKey: ['executions'] });
    },
  });

  const assignMut = useMutation({
    mutationFn: ({ taskId, userId }: { taskId: string; userId: string }) =>
      assignTask(taskId, userId),
    onSuccess: () => {
      setShowAssignDropdown(false);
      qc.invalidateQueries({ queryKey: ['tasks'] });
      qc.invalidateQueries({ queryKey: ['task-detail'] });
    },
  });

  // --- Helpers ---

  const classIcon = (c: string) =>
    c === 'AI' ? (
      <Bot size={14} className="text-purple-500" />
    ) : c === 'MANUAL' ? (
      <User size={14} className="text-slate-500" />
    ) : (
      <ArrowLeftRight size={14} className="text-blue-500" />
    );

  const canRunAI = (task: any) =>
    (task.classification === 'AI' || task.classification === 'HYBRID') &&
    (task.status === 'NOT_STARTED' || task.status === 'WAITING_INPUT');

  const latestExecution = executions?.length ? executions[0] : null;

  const isPaused = taskDetail?.status === 'AI_PAUSED_NEEDS_INPUT';

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-1 flex-wrap">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filter === s
                ? 'bg-blue-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {s.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Task list */}
        <div className="col-span-2 space-y-2">
          {tasks?.map((task: any) => (
            <div
              key={task.id}
              onClick={() => setSelectedTask(task.id)}
              className={`bg-white rounded-lg border p-3 cursor-pointer transition-all ${
                selectedTask === task.id
                  ? 'border-blue-400 ring-1 ring-blue-200'
                  : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {classIcon(task.classification)}
                  <span className="text-sm font-medium text-slate-800 truncate max-w-xs">
                    {task.id.slice(0, 8)}...
                  </span>
                  <span className="text-xs text-slate-400">{task.classification}</span>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={task.status} />

                  {/* Start button for manual start */}
                  {task.status === 'NOT_STARTED' && task.classification === 'MANUAL' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        startMut.mutate(task.id);
                      }}
                      className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded hover:bg-blue-100"
                    >
                      Start
                    </button>
                  )}

                  {/* Run AI button */}
                  {canRunAI(task) && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        executeAIMut.mutate(task.id);
                      }}
                      disabled={executeAIMut.isPending}
                      className="flex items-center gap-1 text-xs bg-purple-50 text-purple-600 px-2 py-0.5 rounded hover:bg-purple-100 disabled:opacity-50"
                    >
                      {executeAIMut.isPending ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Play size={12} />
                      )}
                      Run AI
                    </button>
                  )}

                  {/* Complete button */}
                  {task.status === 'IN_PROGRESS' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        completeMut.mutate(task.id);
                      }}
                      className="text-xs bg-green-50 text-green-600 px-2 py-0.5 rounded hover:bg-green-100"
                    >
                      <CheckCircle2 size={12} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
          {tasks?.length === 0 && (
            <div className="text-center py-8 text-slate-400 text-sm">
              No tasks match this filter.
            </div>
          )}
        </div>

        {/* Task detail panel */}
        <div className="space-y-3">
          {taskDetail ? (
            <>
              {/* Main detail card */}
              <div className="bg-white rounded-xl border border-slate-200 p-4 sticky top-4 space-y-4">
                <h3 className="font-semibold text-slate-900 text-sm">
                  {taskDetail.task_name}
                </h3>
                <p className="text-xs text-slate-500">{taskDetail.task_description}</p>

                {/* Core fields */}
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Status</span>
                    <StatusBadge status={taskDetail.status} />
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Classification</span>
                    <div className="flex items-center gap-1">
                      {classIcon(taskDetail.classification)}
                      <span className="font-medium">{taskDetail.classification}</span>
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-500 flex items-center gap-1">
                      <Shield size={12} /> Trust Level
                    </span>
                    <span className="font-medium">{taskDetail.trust_level ?? 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Priority</span>
                    <span className="font-medium">{taskDetail.priority}</span>
                  </div>
                  {taskDetail.source_type && (
                    <div className="flex justify-between">
                      <span className="text-slate-500 flex items-center gap-1">
                        <FileText size={12} /> Source Type
                      </span>
                      <span className="font-medium text-xs">{taskDetail.source_type}</span>
                    </div>
                  )}
                  {taskDetail.ai_confidence !== undefined && taskDetail.ai_confidence !== null && (
                    <div className="flex justify-between items-center">
                      <span className="text-slate-500 flex items-center gap-1">
                        <Zap size={12} /> AI Confidence
                      </span>
                      <span className="font-medium">
                        {(taskDetail.ai_confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                  {taskDetail.started_at && (
                    <div className="flex justify-between">
                      <span className="text-slate-500 flex items-center gap-1">
                        <Clock size={12} /> Started
                      </span>
                      <span className="text-xs">
                        {new Date(taskDetail.started_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                  {taskDetail.completed_at && (
                    <div className="flex justify-between">
                      <span className="text-slate-500 flex items-center gap-1">
                        <CheckCircle2 size={12} /> Completed
                      </span>
                      <span className="text-xs">
                        {new Date(taskDetail.completed_at).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>

                {/* Dependencies */}
                {taskDetail.depends_on && taskDetail.depends_on.length > 0 && (
                  <div className="border-t border-slate-100 pt-3">
                    <h4 className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1">
                      <GitBranch size={12} /> Dependencies
                    </h4>
                    <div className="space-y-1">
                      {taskDetail.depends_on.map((depId: string) => (
                        <button
                          key={depId}
                          onClick={() => setSelectedTask(depId)}
                          className="block text-xs text-blue-600 hover:underline truncate w-full text-left"
                        >
                          {depId.slice(0, 12)}...
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Assign task */}
                <div className="border-t border-slate-100 pt-3">
                  <h4 className="text-xs font-semibold text-slate-600 mb-2 flex items-center gap-1">
                    <User size={12} /> Assignment
                  </h4>
                  {taskDetail.assigned_to ? (
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-700">
                        {taskDetail.assigned_to_name || taskDetail.assigned_to.slice(0, 12) + '...'}
                      </span>
                      <button
                        onClick={() => setShowAssignDropdown(!showAssignDropdown)}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Reassign
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowAssignDropdown(!showAssignDropdown)}
                      className="flex items-center gap-1 text-xs text-blue-600 hover:underline"
                    >
                      <ChevronDown size={12} /> Assign to user
                    </button>
                  )}
                  {showAssignDropdown && (
                    <div className="mt-2 bg-slate-50 border border-slate-200 rounded-lg p-2 max-h-40 overflow-y-auto">
                      {users?.map((u: any) => (
                        <button
                          key={u.id}
                          onClick={() =>
                            assignMut.mutate({ taskId: taskDetail.id, userId: u.id })
                          }
                          disabled={assignMut.isPending}
                          className="block w-full text-left px-2 py-1.5 text-xs text-slate-700 hover:bg-blue-50 hover:text-blue-700 rounded disabled:opacity-50"
                        >
                          {u.full_name || u.email || u.id.slice(0, 12)}
                        </button>
                      ))}
                      {(!users || users.length === 0) && (
                        <span className="text-xs text-slate-400">No users found</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Run AI action (in detail panel) */}
                {canRunAI(taskDetail) && (
                  <div className="border-t border-slate-100 pt-3">
                    <button
                      onClick={() => executeAIMut.mutate(taskDetail.id)}
                      disabled={executeAIMut.isPending}
                      className="w-full flex items-center justify-center gap-2 bg-purple-600 text-white text-sm font-medium py-2 rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
                    >
                      {executeAIMut.isPending ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Play size={14} />
                      )}
                      Run AI Execution
                    </button>
                  </div>
                )}

                {/* Resume paused execution */}
                {isPaused && latestExecution && (
                  <div className="border-t border-slate-100 pt-3">
                    <h4 className="text-xs font-semibold text-orange-600 mb-2 flex items-center gap-1">
                      <AlertCircle size={12} /> AI Paused — Input Required
                    </h4>
                    <textarea
                      value={resumeInput}
                      onChange={(e) => setResumeInput(e.target.value)}
                      placeholder="Provide the requested input..."
                      rows={3}
                      className="w-full border border-slate-200 rounded-lg p-2 text-xs text-slate-700 resize-none focus:outline-none focus:ring-2 focus:ring-orange-300"
                    />
                    <button
                      onClick={() =>
                        resumeMut.mutate({
                          executionId: latestExecution.id,
                          input: resumeInput,
                        })
                      }
                      disabled={resumeMut.isPending || !resumeInput.trim()}
                      className="mt-2 w-full flex items-center justify-center gap-2 bg-orange-500 text-white text-sm font-medium py-2 rounded-lg hover:bg-orange-600 disabled:opacity-50 transition-colors"
                    >
                      {resumeMut.isPending ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Send size={14} />
                      )}
                      Resume Execution
                    </button>
                  </div>
                )}
              </div>

              {/* Execution status panel */}
              {latestExecution && (
                <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-3">
                  <h4 className="text-xs font-semibold text-slate-700 flex items-center gap-1">
                    <RefreshCw size={12} /> Latest Execution
                  </h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Execution ID</span>
                      <span className="text-xs font-mono text-slate-600">
                        {latestExecution.id.slice(0, 12)}...
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Status</span>
                      <StatusBadge status={latestExecution.status} />
                    </div>
                    {latestExecution.confidence_score !== undefined &&
                      latestExecution.confidence_score !== null && (
                        <div className="flex justify-between items-center">
                          <span className="text-slate-500 flex items-center gap-1">
                            <Zap size={12} /> Confidence
                          </span>
                          <span className="font-medium">
                            {(latestExecution.confidence_score * 100).toFixed(1)}%
                          </span>
                        </div>
                      )}
                    {latestExecution.cost !== undefined && latestExecution.cost !== null && (
                      <div className="flex justify-between items-center">
                        <span className="text-slate-500 flex items-center gap-1">
                          <DollarSign size={12} /> Cost
                        </span>
                        <span className="font-medium">${latestExecution.cost.toFixed(4)}</span>
                      </div>
                    )}
                    {latestExecution.agent_name && (
                      <div className="flex justify-between">
                        <span className="text-slate-500 flex items-center gap-1">
                          <Bot size={12} /> Agent
                        </span>
                        <span className="text-xs font-medium">{latestExecution.agent_name}</span>
                      </div>
                    )}
                    {latestExecution.started_at && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Started</span>
                        <span className="text-xs">
                          {new Date(latestExecution.started_at).toLocaleString()}
                        </span>
                      </div>
                    )}
                    {latestExecution.completed_at && (
                      <div className="flex justify-between">
                        <span className="text-slate-500">Completed</span>
                        <span className="text-xs">
                          {new Date(latestExecution.completed_at).toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* AI Output display */}
              {taskDetail.ai_output && (
                <div className="bg-white rounded-xl border border-slate-200 p-4 space-y-2">
                  <h4 className="text-xs font-semibold text-slate-700 flex items-center gap-1">
                    <Bot size={12} /> AI Output
                  </h4>
                  <pre className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-xs text-slate-700 overflow-x-auto max-h-64 overflow-y-auto whitespace-pre-wrap break-words">
                    {typeof taskDetail.ai_output === 'string'
                      ? taskDetail.ai_output
                      : JSON.stringify(taskDetail.ai_output, null, 2)}
                  </pre>
                </div>
              )}
            </>
          ) : (
            <div className="bg-white rounded-xl border border-slate-200 p-4 text-center text-slate-400 text-sm">
              Select a task to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
