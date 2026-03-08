import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listSourceDefinitions, listProjectSources, selectSources } from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import { Database, Plus } from 'lucide-react';

export default function SourcesTab() {
  const { projectId } = useOutletContext<any>();
  const qc = useQueryClient();
  const [showSelect, setShowSelect] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);

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

  const existingDefIds = new Set(instances?.map((i: any) => i.source_definition_id) || []);

  const toggleSource = (id: string) =>
    setSelected((prev) => prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]);

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
          return (
            <div key={inst.id} className="bg-white rounded-xl border border-slate-200 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Database size={16} className="text-blue-500" />
                  <span className="font-medium text-slate-900">{def?.name || 'Source'}</span>
                  <span className="text-xs text-slate-400">{def?.source_type}</span>
                </div>
                <StatusBadge status={inst.status} />
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
          );
        })}
        {(!instances || instances.length === 0) && (
          <div className="text-center py-8 text-slate-400 text-sm">No sources selected yet.</div>
        )}
      </div>
    </div>
  );
}
