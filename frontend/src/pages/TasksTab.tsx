import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTasks, getTask, updateTask, completeTask } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { Bot, User, ArrowLeftRight, CheckCircle2 } from 'lucide-react';

const STATUS_FILTERS = ['ALL', 'NOT_STARTED', 'IN_PROGRESS', 'AI_PROCESSING', 'IN_REVIEW', 'COMPLETED', 'BLOCKED'];

export default function TasksTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [filter, setFilter] = useState('ALL');
  const [selectedTask, setSelectedTask] = useState<string | null>(null);

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

  const startMut = useMutation({
    mutationFn: (id: string) => updateTask(id, { status: 'IN_PROGRESS' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tasks'] }),
  });

  const completeMut = useMutation({
    mutationFn: (id: string) => completeTask(id, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tasks'] });
      setSelectedTask(null);
    },
  });

  const classIcon = (c: string) =>
    c === 'AI' ? <Bot size={14} className="text-purple-500" /> :
    c === 'MANUAL' ? <User size={14} className="text-slate-500" /> :
    <ArrowLeftRight size={14} className="text-blue-500" />;

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex gap-1 flex-wrap">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              filter === s ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
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
                selectedTask === task.id ? 'border-blue-400' : 'border-slate-200 hover:border-slate-300'
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
                  {task.status === 'NOT_STARTED' && (
                    <button
                      onClick={(e) => { e.stopPropagation(); startMut.mutate(task.id); }}
                      className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded hover:bg-blue-100"
                    >
                      Start
                    </button>
                  )}
                  {task.status === 'IN_PROGRESS' && (
                    <button
                      onClick={(e) => { e.stopPropagation(); completeMut.mutate(task.id); }}
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
            <div className="text-center py-8 text-slate-400 text-sm">No tasks match this filter.</div>
          )}
        </div>

        {/* Task detail */}
        <div>
          {taskDetail ? (
            <div className="bg-white rounded-xl border border-slate-200 p-4 sticky top-4">
              <h3 className="font-semibold text-slate-900 text-sm mb-3">{taskDetail.task_name}</h3>
              <p className="text-xs text-slate-500 mb-4">{taskDetail.task_description}</p>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Status</span>
                  <StatusBadge status={taskDetail.status} />
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Classification</span>
                  <span className="font-medium">{taskDetail.classification}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Trust Level</span>
                  <span className="font-medium">{taskDetail.trust_level}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Priority</span>
                  <span className="font-medium">{taskDetail.priority}</span>
                </div>
                {taskDetail.started_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Started</span>
                    <span className="text-xs">{new Date(taskDetail.started_at).toLocaleString()}</span>
                  </div>
                )}
                {taskDetail.completed_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Completed</span>
                    <span className="text-xs">{new Date(taskDetail.completed_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
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
