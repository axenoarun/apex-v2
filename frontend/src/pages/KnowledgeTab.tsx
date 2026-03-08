import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { listKnowledge } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { BookOpen, Search, Tag, TrendingUp, Calendar, Star } from 'lucide-react';

const KNOWLEDGE_TYPES = ['ALL', 'PATTERN', 'BEST_PRACTICE', 'ANTI_PATTERN', 'TEMPLATE', 'METRIC'] as const;

const typeBadgeColors: Record<string, string> = {
  PATTERN: 'bg-blue-100 text-blue-700',
  BEST_PRACTICE: 'bg-green-100 text-green-700',
  ANTI_PATTERN: 'bg-red-100 text-red-700',
  TEMPLATE: 'bg-purple-100 text-purple-700',
  METRIC: 'bg-amber-100 text-amber-700',
};

export default function KnowledgeTab() {
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [searchText, setSearchText] = useState('');

  const { data: knowledge, isLoading } = useQuery({
    queryKey: ['knowledge', typeFilter],
    queryFn: () => {
      const params: Record<string, string> = {};
      if (typeFilter !== 'ALL') params.knowledge_type = typeFilter;
      return listKnowledge(params).then((r) => r.data);
    },
  });

  const filtered = useMemo(() => {
    if (!knowledge) return [];
    if (!searchText.trim()) return knowledge;
    const lower = searchText.toLowerCase();
    return knowledge.filter((k: any) => {
      const title = (k.title || k.summary || '').toLowerCase();
      const summary = (k.summary || '').toLowerCase();
      const tags = (k.tags || []).join(' ').toLowerCase();
      return title.includes(lower) || summary.includes(lower) || tags.includes(lower);
    });
  }, [knowledge, searchText]);

  if (isLoading) return <div className="text-slate-500 text-sm">Loading knowledge entries...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Knowledge Base</h2>
        <span className="text-sm text-slate-400">{filtered?.length || 0} entries</span>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search knowledge entries..."
          className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>

      {/* Type filters */}
      <div className="flex gap-1 flex-wrap">
        {KNOWLEDGE_TYPES.map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              typeFilter === t ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {t.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Knowledge cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filtered?.map((entry: any) => (
          <div key={entry.id} className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
            {/* Header */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <BookOpen size={16} className="text-slate-500 flex-shrink-0" />
                <h3 className="text-sm font-semibold text-slate-900 truncate">
                  {entry.title || entry.summary || `Knowledge ${entry.id.slice(0, 8)}`}
                </h3>
              </div>
              <span
                className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                  typeBadgeColors[entry.knowledge_type] || 'bg-slate-100 text-slate-600'
                }`}
              >
                {(entry.knowledge_type || 'UNKNOWN').replace(/_/g, ' ')}
              </span>
            </div>

            {/* Summary */}
            {entry.summary && (
              <p className="text-sm text-slate-600 line-clamp-2">{entry.summary}</p>
            )}

            {/* Stats row */}
            <div className="flex items-center gap-4 text-xs text-slate-500">
              <div className="flex items-center gap-1" title="Confidence score">
                <Star size={12} className="text-amber-500" />
                <span className="font-medium">{((entry.confidence_score ?? 0) * 100).toFixed(0)}%</span>
              </div>
              <div className="flex items-center gap-1" title="Times used / successful">
                <TrendingUp size={12} className="text-green-500" />
                <span>
                  {entry.times_used ?? 0} used / {entry.times_successful ?? 0} success
                </span>
              </div>
            </div>

            {/* Source project */}
            {entry.source_project_id && (
              <div className="text-xs text-slate-400">
                Source: <span className="font-mono">{entry.source_project_id.slice(0, 12)}...</span>
              </div>
            )}

            {/* Tags */}
            {entry.tags && entry.tags.length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                <Tag size={12} className="text-slate-400" />
                {entry.tags.map((tag: string, i: number) => (
                  <span
                    key={i}
                    className="inline-block bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}

            {/* Created date */}
            {entry.created_at && (
              <div className="flex items-center gap-1 text-xs text-slate-400">
                <Calendar size={12} />
                <span>{new Date(entry.created_at).toLocaleDateString()}</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Empty state */}
      {(!filtered || filtered.length === 0) && (
        <div className="text-center py-12">
          <BookOpen size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-400 text-sm">
            {searchText || typeFilter !== 'ALL'
              ? 'No knowledge entries match your filters.'
              : 'No knowledge entries yet. Knowledge is extracted from completed projects.'}
          </p>
        </div>
      )}
    </div>
  );
}
