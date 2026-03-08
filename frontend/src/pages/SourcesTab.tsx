import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSourceDefinitions, listProjectSources, selectSources, updateSource } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { Database, Plus, ChevronDown, ChevronUp, Settings } from 'lucide-react';

const LAYER_STATUSES = ['NOT_STARTED', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED'];

export default function SourcesTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [showSelect, setShowSelect] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  const { data: definitions } = useQuery({
    queryKey: ['source-definitions'],
    queryFn: () => listSourceDefinitions().then((r) => r.data),
  });

  const { data: instances } = useQuery({
    queryKey: ['project-sources', projectId],
    queryFn: () => listProjectSources(projectId).then((r) => r.data),
  });

  const selectMut = useMutation({
    mutationFn: () => selectSources(projectId, selected),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project-sources'] });
      setShowSelect(false);
      setSelected([]);
    },
  });

  const updateMut = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) => updateSource(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-sources'] }),
  });

  const existingDefIds = new Set(instances?.map((i: any) => i.source_definition_id) || []);

  const toggleSource = (id: string) =>
    setSelected((prev) => prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]);

  const handleLayerUpdate = (instanceId: string, layer: string, status: string) => {
    updateMut.mutate({ id: instanceId, data: { [`${layer}_status`]: status } });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Data Sources</h2>
        <button
          onClick={() => setShowSelect(true)}
          className="flex items-center gap-1.5 bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-blue-700"
        >
          <Plus size={14} /> Add Sources
        </button>
      </div>

      {/* Summary cards */}
      {instances && instances.length > 0 && (
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
            <div className="text-2xl font-bold text-slate-700">{instances.length}</div>
            <div className="text-xs text-slate-500">Total Sources</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
            <div className="text-2xl font-bold text-cyan-600">
              {instances.filter((i: any) => i.pilot_status === 'COMPLETED').length}
            </div>
            <div className="text-xs text-slate-500">Pilot Ready</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
            <div className="text-2xl font-bold text-blue-600">
              {instances.filter((i: any) => i.dev_status === 'COMPLETED').length}
            </div>
            <div className="text-xs text-slate-500">Dev Ready</div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-3 text-center">
            <div className="text-2xl font-bold text-green-600">
              {instances.filter((i: any) => i.prod_status === 'COMPLETED').length}
            </div>
            <div className="text-xs text-slate-500">Prod Ready</div>
          </div>
        </div>
      )}

      {showSelect && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-medium text-slate-900 mb-3">Select Data Sources</h3>
          <div className="space-y-2">
            {definitions?.filter((d: any) => !existingDefIds.has(d.id)).map((def: any) => (
              <label key={def.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selected.includes(def.id)}
                  onChange={() => toggleSource(def.id)}
                  className="rounded"
                />
                <div className="flex-1">
                  <span className="text-sm font-medium">{def.name}</span>
                  <span className="text-xs text-slate-500 ml-2">{def.source_type}</span>
                  {def.is_mandatory && <span className="text-xs bg-red-50 text-red-600 ml-2 px-1 rounded">Required</span>}
                </div>
                <span className="text-xs text-slate-400">{def.business_type}</span>
              </label>
            ))}
            {definitions?.filter((d: any) => !existingDefIds.has(d.id)).length === 0 && (
              <p className="text-sm text-slate-400 py-2">All available sources have been added.</p>
            )}
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => selectMut.mutate()}
              disabled={selected.length === 0}
              className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm disabled:opacity-50"
            >
              Add Selected
            </button>
            <button onClick={() => setShowSelect(false)} className="text-sm text-slate-500 hover:text-slate-700">Cancel</button>
          </div>
        </div>
      )}

      {/* Source instances */}
      <div className="space-y-3">
        {instances?.map((inst: any) => {
          const def = definitions?.find((d: any) => d.id === inst.source_definition_id);
          const isExpanded = expanded === inst.id;
          return (
            <div key={inst.id} className="bg-white rounded-xl border border-slate-200">
              <div
                className="p-4 cursor-pointer hover:bg-slate-50 transition-colors"
                onClick={() => setExpanded(isExpanded ? null : inst.id)}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Database size={16} className="text-blue-500" />
                    <span className="font-medium text-slate-900">{def?.name || 'Source'}</span>
                    <span className="text-xs text-slate-400">{def?.source_type}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={inst.status} />
                    {isExpanded ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-3 text-xs">
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <div className="text-slate-500 mb-1">Pilot</div>
                    <StatusBadge status={inst.pilot_status || 'NOT_STARTED'} />
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <div className="text-slate-500 mb-1">Dev</div>
                    <StatusBadge status={inst.dev_status || 'NOT_STARTED'} />
                  </div>
                  <div className="bg-slate-50 rounded-lg p-2 text-center">
                    <div className="text-slate-500 mb-1">Prod</div>
                    <StatusBadge status={inst.prod_status || 'NOT_STARTED'} />
                  </div>
                </div>
              </div>

              {/* Expanded detail */}
              {isExpanded && (
                <div className="border-t border-slate-200 p-4 bg-slate-50 space-y-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    <Settings size={14} /> Update Layer Status
                  </div>
                  {['pilot', 'dev', 'prod'].map((layer) => (
                    <div key={layer} className="flex items-center gap-3">
                      <span className="text-xs font-medium text-slate-600 w-12 capitalize">{layer}</span>
                      <div className="flex gap-1">
                        {LAYER_STATUSES.map((s) => (
                          <button
                            key={s}
                            onClick={(e) => { e.stopPropagation(); handleLayerUpdate(inst.id, layer, s); }}
                            className={`px-2 py-0.5 rounded text-xs ${
                              inst[`${layer}_status`] === s
                                ? 'bg-blue-600 text-white'
                                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                            }`}
                          >
                            {s.replace(/_/g, ' ')}
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {def?.description && (
                    <div className="text-xs text-slate-500 mt-2">
                      <span className="font-medium">Description:</span> {def.description}
                    </div>
                  )}
                  {def?.artifacts && (
                    <div className="text-xs text-slate-500">
                      <span className="font-medium">Artifacts:</span>{' '}
                      {Array.isArray(def.artifacts) ? def.artifacts.join(', ') : JSON.stringify(def.artifacts)}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {(!instances || instances.length === 0) && (
          <div className="text-center py-8 text-slate-400 text-sm">No sources selected yet.</div>
        )}
      </div>
    </div>
  );
}
