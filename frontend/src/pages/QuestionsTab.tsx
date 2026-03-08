import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listQuestions, answerQuestion, getQuestionStats, listProjectPhases, generateQuestions } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { HelpCircle, Send, Bot, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

export default function QuestionsTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [filter, setFilter] = useState('ALL');
  const [answerText, setAnswerText] = useState<Record<string, string>>({});
  const [showGenerate, setShowGenerate] = useState(false);
  const [genPhaseId, setGenPhaseId] = useState('');
  const [groupByRole, setGroupByRole] = useState(false);

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

  const { data: phases } = useQuery({
    queryKey: ['project-phases', projectId],
    queryFn: () => listProjectPhases(projectId).then((r) => r.data),
  });

  const answerMut = useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) => answerQuestion(id, answer),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['questions'] });
      qc.invalidateQueries({ queryKey: ['question-stats'] });
    },
  });

  const generateMut = useMutation({
    mutationFn: () => generateQuestions(projectId, genPhaseId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['questions'] });
      qc.invalidateQueries({ queryKey: ['question-stats'] });
      setShowGenerate(false);
      setGenPhaseId('');
    },
  });

  const handleAnswer = (id: string) => {
    const text = answerText[id];
    if (text?.trim()) {
      answerMut.mutate({ id, answer: text });
      setAnswerText((prev) => ({ ...prev, [id]: '' }));
    }
  };

  // Group questions by role if toggled
  const groupedQuestions = groupByRole && questions
    ? questions.reduce((acc: Record<string, any[]>, q: any) => {
        const role = q.target_role || 'General';
        if (!acc[role]) acc[role] = [];
        acc[role].push(q);
        return acc;
      }, {} as Record<string, any[]>)
    : null;

  const completionPct = stats && stats.total > 0
    ? Math.round((stats.answered / stats.total) * 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        {[
          { label: 'Total', value: stats?.total || 0, color: 'text-slate-700' },
          { label: 'Pending', value: stats?.pending || 0, color: 'text-amber-600' },
          { label: 'Answered', value: stats?.answered || 0, color: 'text-green-600' },
          { label: 'Skipped', value: stats?.skipped || 0, color: 'text-slate-500' },
          { label: 'Completion', value: `${completionPct}%`, color: 'text-blue-600' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-3 text-center">
            <div className={`text-2xl font-bold ${color}`}>{value}</div>
            <div className="text-xs text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Completion bar */}
      {stats && stats.total > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-3">
          <div className="flex justify-between text-xs text-slate-500 mb-1">
            <span>Progress</span>
            <span>{stats.answered}/{stats.total} answered</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2">
            <div className="bg-green-500 h-2 rounded-full transition-all" style={{ width: `${completionPct}%` }} />
          </div>
        </div>
      )}

      {/* Controls */}
      <div className="flex items-center justify-between">
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
        <div className="flex gap-2">
          <button
            onClick={() => setGroupByRole(!groupByRole)}
            className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs ${
              groupByRole ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
            }`}
          >
            Group by Role
          </button>
          <button
            onClick={() => setShowGenerate(!showGenerate)}
            className="flex items-center gap-1.5 bg-purple-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-purple-700"
          >
            <Sparkles size={14} /> Generate AI Questions
          </button>
        </div>
      </div>

      {/* Generate questions panel */}
      {showGenerate && (
        <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Bot size={16} className="text-purple-600" />
            <span className="font-medium text-purple-900">Generate Questions with AI</span>
          </div>
          <p className="text-xs text-purple-700 mb-3">
            AI will analyze the selected phase and generate targeted questions for each stakeholder role.
          </p>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="text-xs text-purple-700 mb-1 block">Select Phase</label>
              <select
                value={genPhaseId}
                onChange={(e) => setGenPhaseId(e.target.value)}
                className="w-full border border-purple-300 rounded-lg px-3 py-1.5 text-sm bg-white"
              >
                <option value="">Choose a phase...</option>
                {phases?.map((p: any) => (
                  <option key={p.id} value={p.id}>{p.phase_name || `Phase ${p.order_index}`}</option>
                ))}
              </select>
            </div>
            <button
              onClick={() => generateMut.mutate()}
              disabled={!genPhaseId || generateMut.isPending}
              className="bg-purple-600 text-white px-4 py-1.5 rounded-lg text-sm hover:bg-purple-700 disabled:opacity-50"
            >
              {generateMut.isPending ? 'Generating...' : 'Generate'}
            </button>
            <button onClick={() => setShowGenerate(false)} className="text-sm text-purple-600 hover:text-purple-800">
              Cancel
            </button>
          </div>
          {generateMut.isSuccess && (
            <div className="mt-2 text-xs text-green-700 bg-green-50 rounded p-2">
              Questions generation queued. They will appear once processing completes.
            </div>
          )}
        </div>
      )}

      {/* Questions list - grouped or flat */}
      {groupedQuestions ? (
        <div className="space-y-4">
          {Object.entries(groupedQuestions).map(([role, roleQuestions]) => (
            <RoleGroup key={role} role={role} questions={roleQuestions as any[]} answerText={answerText} setAnswerText={setAnswerText} handleAnswer={handleAnswer} />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {questions?.map((q: any) => (
            <QuestionCard key={q.id} q={q} answerText={answerText} setAnswerText={setAnswerText} handleAnswer={handleAnswer} />
          ))}
          {(!questions || questions.length === 0) && (
            <div className="text-center py-8 text-slate-400 text-sm">
              No questions yet. Use "Generate AI Questions" to create targeted questions for stakeholders.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RoleGroup({ role, questions, answerText, setAnswerText, handleAnswer }: {
  role: string; questions: any[]; answerText: Record<string, string>;
  setAnswerText: React.Dispatch<React.SetStateAction<Record<string, string>>>; handleAnswer: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const answered = questions.filter((q) => q.status === 'ANSWERED').length;

  return (
    <div className="bg-white rounded-xl border border-slate-200">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3 hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-900">{role}</span>
          <span className="text-xs text-slate-400">({answered}/{questions.length} answered)</span>
        </div>
        {open ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
      </button>
      {open && (
        <div className="border-t border-slate-100 p-3 space-y-3">
          {questions.map((q) => (
            <QuestionCard key={q.id} q={q} answerText={answerText} setAnswerText={setAnswerText} handleAnswer={handleAnswer} />
          ))}
        </div>
      )}
    </div>
  );
}

function QuestionCard({ q, answerText, setAnswerText, handleAnswer }: {
  q: any; answerText: Record<string, string>;
  setAnswerText: React.Dispatch<React.SetStateAction<Record<string, string>>>; handleAnswer: (id: string) => void;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-start gap-2">
          <HelpCircle size={16} className="text-blue-500 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm text-slate-900">{q.question_text}</p>
            <div className="flex gap-2 mt-1">
              <span className="text-xs text-slate-400">Role: {q.target_role}</span>
              <span className="text-xs text-slate-400">Type: {q.question_type}</span>
              {q.maps_to_document_field && (
                <span className="text-xs text-indigo-400">Maps to: {q.maps_to_document_field}</span>
              )}
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
  );
}
