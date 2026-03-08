import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listQuestions, answerQuestion, getQuestionStats } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { HelpCircle, Send } from 'lucide-react';

export default function QuestionsTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [filter, setFilter] = useState('ALL');
  const [answerText, setAnswerText] = useState<Record<string, string>>({});

  const { data: questions } = useQuery({
    queryKey: ['questions', projectId, filter],
    queryFn: () => {
      const params: Record<string, string> = { project_id: projectId };
      if (filter !== 'ALL') params.status = filter;
      return listQuestions(params).then((r) => r.data);
    },
  });

  const { data: stats } = useQuery({
    queryKey: ['question-stats', projectId],
    queryFn: () => getQuestionStats(projectId).then((r) => r.data),
  });

  const answerMut = useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) => answerQuestion(id, answer),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['questions'] });
      qc.invalidateQueries({ queryKey: ['question-stats'] });
    },
  });

  const handleAnswer = (id: string) => {
    const text = answerText[id];
    if (text?.trim()) {
      answerMut.mutate({ id, answer: text });
      setAnswerText((prev) => ({ ...prev, [id]: '' }));
    }
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Total', value: stats?.total || 0, color: 'text-slate-700' },
          { label: 'Pending', value: stats?.pending || 0, color: 'text-amber-600' },
          { label: 'Answered', value: stats?.answered || 0, color: 'text-green-600' },
          { label: 'Skipped', value: stats?.skipped || 0, color: 'text-slate-500' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-3 text-center">
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-1">
        {['ALL', 'PENDING', 'ANSWERED', 'SKIPPED'].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-full text-xs font-medium ${
              filter === s ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Questions list */}
      <div className="space-y-3">
        {questions?.map((q: any) => (
          <div key={q.id} className="bg-white rounded-xl border border-slate-200 p-4">
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-start gap-2">
                <HelpCircle size={16} className="text-blue-500 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm text-slate-900">{q.question_text}</p>
                  <div className="flex gap-2 mt-1">
                    <span className="text-xs text-slate-400">Role: {q.target_role}</span>
                    <span className="text-xs text-slate-400">Type: {q.question_type}</span>
                  </div>
                </div>
              </div>
              <StatusBadge status={q.status} />
            </div>

            {q.answer ? (
              <div className="ml-6 mt-2 bg-green-50 rounded-lg p-2 text-sm text-green-800">
                {q.answer}
              </div>
            ) : (
              <div className="ml-6 mt-2 flex gap-2">
                <input
                  value={answerText[q.id] || ''}
                  onChange={(e) => setAnswerText((prev) => ({ ...prev, [q.id]: e.target.value }))}
                  placeholder="Type your answer..."
                  className="flex-1 border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
                  onKeyDown={(e) => e.key === 'Enter' && handleAnswer(q.id)}
                />
                <button
                  onClick={() => handleAnswer(q.id)}
                  disabled={!answerText[q.id]?.trim()}
                  className="bg-blue-600 text-white p-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  <Send size={14} />
                </button>
              </div>
            )}
          </div>
        ))}
        {(!questions || questions.length === 0) && (
          <div className="text-center py-8 text-slate-400 text-sm">No questions yet.</div>
        )}
      </div>
    </div>
  );
}
