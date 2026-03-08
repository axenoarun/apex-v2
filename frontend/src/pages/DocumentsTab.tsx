import { useState, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  listDocumentTemplates,
  listProjectDocuments,
  getDocument,
  updateDocument,
  reviewDocument,
  generateDocument,
  listProjectPhases,
} from '../api/endpoints';
import StatusBadge from '../components/StatusBadge';
import {
  FileText,
  Plus,
  Check,
  X,
  ChevronRight,
  Save,
  Eye,
  Edit3,
  Loader2,
  Sparkles,
  ArrowLeft,
  Clock,
  FileType,
  Layers,
  Hash,
} from 'lucide-react';

const STATUS_STEPS = ['NOT_STARTED', 'AI_DRAFTING', 'DRAFT', 'IN_REVIEW', 'FINAL'] as const;

function StatusLifecycle({ current }: { current: string }) {
  const currentIdx = STATUS_STEPS.indexOf(current as (typeof STATUS_STEPS)[number]);
  return (
    <div className="flex items-center gap-1">
      {STATUS_STEPS.map((step, idx) => {
        const isActive = step === current;
        const isPast = currentIdx >= 0 && idx < currentIdx;
        let dotClass = 'w-2.5 h-2.5 rounded-full border-2 transition-colors';
        if (isActive) {
          dotClass += ' bg-blue-500 border-blue-500';
        } else if (isPast) {
          dotClass += ' bg-green-400 border-green-400';
        } else {
          dotClass += ' bg-slate-200 border-slate-300';
        }
        return (
          <div key={step} className="flex items-center gap-1">
            <div className="flex flex-col items-center">
              <div className={dotClass} title={step.replace(/_/g, ' ')} />
            </div>
            {idx < STATUS_STEPS.length - 1 && (
              <div
                className={`w-4 h-0.5 ${isPast ? 'bg-green-400' : 'bg-slate-200'}`}
              />
            )}
          </div>
        );
      })}
      <span className="ml-2 text-xs text-slate-500">{current.replace(/_/g, ' ')}</span>
    </div>
  );
}

interface GenerateModalProps {
  template: any;
  phases: any[];
  onClose: () => void;
  onGenerate: (phaseInstanceId: string) => void;
  isPending: boolean;
}

function GenerateModal({ template, phases, onClose, onGenerate, isPending }: GenerateModalProps) {
  const [selectedPhase, setSelectedPhase] = useState(phases.length > 0 ? phases[0].id : '');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Generate Document with AI</h3>
        <p className="text-sm text-slate-500 mb-4">
          Template: <span className="font-medium text-slate-700">{template.name}</span>
        </p>

        {template.description && (
          <p className="text-xs text-slate-500 mb-3 bg-slate-50 rounded-lg p-2">{template.description}</p>
        )}

        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">Select Phase</label>
          <select
            value={selectedPhase}
            onChange={(e) => setSelectedPhase(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            {phases.map((phase: any) => (
              <option key={phase.id} value={phase.id}>
                {phase.phase_name || phase.name || phase.definition_name || `Phase ${phase.sequence_order}`}
                {phase.status ? ` (${phase.status.replace(/_/g, ' ')})` : ''}
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs text-slate-400 mb-4 flex items-center gap-1.5">
          <FileType size={12} />
          <span>Output format: {template.output_format || 'N/A'}</span>
        </div>

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onGenerate(selectedPhase)}
            disabled={isPending || !selectedPhase}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 rounded-lg transition-colors"
          >
            {isPending ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Sparkles size={14} />
                Generate
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

function DocumentSections({ content }: { content: any }) {
  if (!content) return null;

  if (typeof content === 'string') {
    return <pre className="whitespace-pre-wrap text-sm text-slate-700 font-mono bg-slate-50 rounded-lg p-4">{content}</pre>;
  }

  if (typeof content === 'object' && content.sections && Array.isArray(content.sections)) {
    return (
      <div className="space-y-4">
        {content.sections.map((section: any, idx: number) => (
          <div key={idx} className="border border-slate-100 rounded-lg p-4 bg-slate-50/50">
            <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
              <Layers size={14} className="text-blue-400" />
              {section.title || section.heading || `Section ${idx + 1}`}
            </h4>
            <div className="text-sm text-slate-600 whitespace-pre-wrap">
              {typeof section.content === 'string'
                ? section.content
                : JSON.stringify(section.content, null, 2)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (typeof content === 'object') {
    const entries = Object.entries(content);
    if (entries.length === 0) return <p className="text-sm text-slate-400 italic">Empty content</p>;
    return (
      <div className="space-y-3">
        {entries.map(([key, value]) => (
          <div key={key} className="border border-slate-100 rounded-lg p-4 bg-slate-50/50">
            <h4 className="text-sm font-semibold text-slate-800 mb-2 flex items-center gap-2">
              <Layers size={14} className="text-blue-400" />
              {key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </h4>
            <div className="text-sm text-slate-600 whitespace-pre-wrap">
              {typeof value === 'string' ? value : JSON.stringify(value, null, 2)}
            </div>
          </div>
        ))}
      </div>
    );
  }

  return null;
}

interface DocumentDetailProps {
  documentId: string;
  templateName: string;
  onBack: () => void;
}

function DocumentDetail({ documentId, templateName, onBack }: DocumentDetailProps) {
  const qc = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');

  const { data: doc, isLoading } = useQuery({
    queryKey: ['document-detail', documentId],
    queryFn: () => getDocument(documentId).then((r) => r.data),
  });

  const updateMut = useMutation({
    mutationFn: (content: string) => {
      let parsed: any;
      try {
        parsed = JSON.parse(content);
      } catch {
        parsed = content;
      }
      return updateDocument(documentId, { content: parsed });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['document-detail', documentId] });
      qc.invalidateQueries({ queryKey: ['project-docs'] });
      setIsEditing(false);
    },
  });

  const reviewMut = useMutation({
    mutationFn: (approved: boolean) => reviewDocument(documentId, { approved }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['document-detail', documentId] });
      qc.invalidateQueries({ queryKey: ['project-docs'] });
    },
  });

  const startEditing = useCallback(() => {
    if (!doc) return;
    const raw = typeof doc.content === 'string' ? doc.content : JSON.stringify(doc.content, null, 2);
    setEditContent(raw);
    setIsEditing(true);
  }, [doc]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 size={24} className="animate-spin text-blue-500" />
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">Document not found.</div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors"
        >
          <ArrowLeft size={18} />
        </button>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <FileText size={18} className="text-blue-500" />
            <h2 className="text-lg font-semibold text-slate-900">{templateName}</h2>
            <span className="flex items-center gap-1 text-sm font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md">
              <Hash size={12} />
              v{doc.version}
            </span>
          </div>
          <div className="mt-1">
            <StatusLifecycle current={doc.status} />
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-slate-400 block text-xs">Status</span>
            <StatusBadge status={doc.status} />
          </div>
          <div>
            <span className="text-slate-400 block text-xs">Version</span>
            <span className="font-medium text-slate-700">v{doc.version}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-xs">Generated By</span>
            <span className="font-medium text-slate-700">{doc.generated_by || 'N/A'}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-xs">Created</span>
            <span className="font-medium text-slate-700 flex items-center gap-1">
              <Clock size={12} />
              {new Date(doc.created_at).toLocaleString()}
            </span>
          </div>
        </div>
        {doc.updated_at && doc.updated_at !== doc.created_at && (
          <div className="mt-2 text-xs text-slate-400">
            Last updated: {new Date(doc.updated_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {doc.status === 'DRAFT' && (
          <button
            onClick={isEditing ? () => setIsEditing(false) : startEditing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors"
          >
            {isEditing ? <Eye size={14} /> : <Edit3 size={14} />}
            {isEditing ? 'Preview' : 'Edit Content'}
          </button>
        )}
        {(doc.status === 'DRAFT' || doc.status === 'IN_REVIEW') && (
          <>
            <button
              onClick={() => reviewMut.mutate(true)}
              disabled={reviewMut.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-lg transition-colors disabled:opacity-50"
            >
              <Check size={14} />
              Approve
            </button>
            <button
              onClick={() => reviewMut.mutate(false)}
              disabled={reviewMut.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50"
            >
              <X size={14} />
              Request Revision
            </button>
          </>
        )}
      </div>

      {/* Content */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Document Content</h3>
        {isEditing ? (
          <div className="space-y-3">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              rows={20}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsEditing(false)}
                className="px-4 py-2 text-sm text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => updateMut.mutate(editContent)}
                disabled={updateMut.isPending}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 rounded-lg transition-colors"
              >
                {updateMut.isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Save size={14} />
                )}
                Save Changes
              </button>
            </div>
          </div>
        ) : doc.content ? (
          <DocumentSections content={doc.content} />
        ) : (
          <p className="text-sm text-slate-400 italic py-4">
            {doc.status === 'AI_DRAFTING'
              ? 'AI is currently generating this document...'
              : doc.status === 'NOT_STARTED'
                ? 'Document has not been generated yet.'
                : 'No content available.'}
          </p>
        )}
      </div>
    </div>
  );
}

export default function DocumentsTab() {
  const { projectId, project } = useOutletContext<any>();
  const qc = useQueryClient();

  const [generateModalTemplate, setGenerateModalTemplate] = useState<any>(null);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocName, setSelectedDocName] = useState<string>('Document');

  const { data: templates } = useQuery({
    queryKey: ['doc-templates'],
    queryFn: () => listDocumentTemplates().then((r) => r.data),
  });

  const { data: documents } = useQuery({
    queryKey: ['project-docs', projectId],
    queryFn: () => listProjectDocuments(projectId).then((r) => r.data),
  });

  const { data: phases } = useQuery({
    queryKey: ['project-phases', projectId],
    queryFn: () => listProjectPhases(projectId).then((r) => r.data),
  });

  const generateMut = useMutation({
    mutationFn: (data: { template_id: string; phase_instance_id: string }) =>
      generateDocument({
        project_id: projectId,
        template_id: data.template_id,
        phase_instance_id: data.phase_instance_id,
        async_mode: true,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project-docs'] });
      setGenerateModalTemplate(null);
    },
  });

  const reviewMut = useMutation({
    mutationFn: ({ id, approved }: { id: string; approved: boolean }) => reviewDocument(id, { approved }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project-docs'] }),
  });

  const handleGenerate = (phaseInstanceId: string) => {
    if (!generateModalTemplate) return;
    generateMut.mutate({
      template_id: generateModalTemplate.id,
      phase_instance_id: phaseInstanceId,
    });
  };

  const openDocDetail = (doc: any, name: string) => {
    setSelectedDocId(doc.id);
    setSelectedDocName(name);
  };

  // If a document is selected, show the detail view
  if (selectedDocId) {
    return (
      <DocumentDetail
        documentId={selectedDocId}
        templateName={selectedDocName}
        onBack={() => setSelectedDocId(null)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Documents</h2>
        <span className="text-xs text-slate-400">
          {documents?.length || 0} document{documents?.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Templates */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <Sparkles size={14} className="text-purple-500" />
          Generate from Template
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {templates?.map((t: any) => (
            <button
              key={t.id}
              onClick={() => setGenerateModalTemplate(t)}
              className="flex flex-col items-start gap-1.5 border border-slate-200 text-left px-4 py-3 rounded-xl text-sm hover:bg-blue-50 hover:border-blue-200 transition-colors group"
            >
              <div className="flex items-center gap-2 w-full">
                <Plus size={14} className="text-blue-500 group-hover:text-blue-600" />
                <span className="font-medium text-slate-800 group-hover:text-blue-700 truncate flex-1">
                  {t.name}
                </span>
              </div>
              {t.description && (
                <p className="text-xs text-slate-400 line-clamp-2">{t.description}</p>
              )}
              <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                <span className="flex items-center gap-1">
                  <FileType size={10} />
                  {t.output_format || 'N/A'}
                </span>
                {t.phase_definition_name && (
                  <span className="flex items-center gap-1">
                    <Layers size={10} />
                    {t.phase_definition_name}
                  </span>
                )}
                {t.phase_definition_id && !t.phase_definition_name && (
                  <span className="flex items-center gap-1">
                    <Layers size={10} />
                    Phase linked
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
        {(!templates || templates.length === 0) && (
          <p className="text-sm text-slate-400 text-center py-4">No templates available.</p>
        )}
      </div>

      {/* Document instances */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-700">Generated Documents</h3>
        {documents?.map((doc: any) => {
          const tmpl = templates?.find((t: any) => t.id === doc.document_template_id);
          const docName = tmpl?.name || 'Document';
          return (
            <div
              key={doc.id}
              className="bg-white rounded-xl border border-slate-200 p-4 hover:border-blue-200 hover:shadow-sm transition-all cursor-pointer group"
              onClick={() => openDocDetail(doc, docName)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <FileText size={18} className="text-blue-500 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-900 truncate">{docName}</span>
                      <span className="flex items-center gap-0.5 text-xs font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded shrink-0">
                        <Hash size={10} />
                        v{doc.version}
                      </span>
                    </div>
                    <div className="mt-1">
                      <StatusLifecycle current={doc.status} />
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  <StatusBadge status={doc.status} />
                  {(doc.status === 'DRAFT' || doc.status === 'IN_REVIEW') && (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => reviewMut.mutate({ id: doc.id, approved: true })}
                        disabled={reviewMut.isPending}
                        className="p-1.5 rounded-lg hover:bg-green-50 text-green-600 transition-colors"
                        title="Approve"
                      >
                        <Check size={16} />
                      </button>
                      <button
                        onClick={() => reviewMut.mutate({ id: doc.id, approved: false })}
                        disabled={reviewMut.isPending}
                        className="p-1.5 rounded-lg hover:bg-red-50 text-red-600 transition-colors"
                        title="Request Revision"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  )}
                  <ChevronRight
                    size={16}
                    className="text-slate-300 group-hover:text-blue-400 transition-colors"
                  />
                </div>
              </div>
              <div className="mt-2 text-xs text-slate-500 flex items-center gap-3">
                <span>Generated by: {doc.generated_by || 'N/A'}</span>
                <span className="flex items-center gap-1">
                  <Clock size={10} />
                  {new Date(doc.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          );
        })}
        {(!documents || documents.length === 0) && (
          <div className="text-center py-12 text-slate-400 text-sm bg-white rounded-xl border border-slate-200">
            <FileText size={32} className="mx-auto mb-2 text-slate-300" />
            <p>No documents generated yet.</p>
            <p className="text-xs mt-1">Use the templates above to generate your first document.</p>
          </div>
        )}
      </div>

      {/* Generate Modal */}
      {generateModalTemplate && phases && (
        <GenerateModal
          template={generateModalTemplate}
          phases={phases}
          onClose={() => setGenerateModalTemplate(null)}
          onGenerate={handleGenerate}
          isPending={generateMut.isPending}
        />
      )}
    </div>
  );
}
