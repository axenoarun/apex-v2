import clsx from 'clsx';

const colorMap: Record<string, string> = {
  NOT_STARTED: 'bg-slate-100 text-slate-700',
  PENDING: 'bg-amber-100 text-amber-700',
  IN_PROGRESS: 'bg-blue-100 text-blue-700',
  AI_PROCESSING: 'bg-purple-100 text-purple-700',
  AI_PAUSED_NEEDS_INPUT: 'bg-orange-100 text-orange-700',
  WAITING_INPUT: 'bg-amber-100 text-amber-700',
  IN_REVIEW: 'bg-indigo-100 text-indigo-700',
  COMPLETED: 'bg-green-100 text-green-700',
  FINAL: 'bg-green-100 text-green-700',
  BLOCKED: 'bg-red-100 text-red-700',
  OVERDUE: 'bg-red-100 text-red-700',
  ACTIVE: 'bg-green-100 text-green-700',
  PROPOSED: 'bg-cyan-100 text-cyan-700',
  ACCEPTED: 'bg-green-100 text-green-700',
  REJECTED: 'bg-red-100 text-red-700',
  DEFERRED: 'bg-slate-100 text-slate-600',
  DRAFT: 'bg-yellow-100 text-yellow-700',
  REVISION_REQUESTED: 'bg-orange-100 text-orange-700',
  EXPORTED: 'bg-teal-100 text-teal-700',
  ANSWERED: 'bg-green-100 text-green-700',
  PAUSED: 'bg-orange-100 text-orange-700',
  AVAILABLE: 'bg-green-100 text-green-700',
  NOT_AVAILABLE: 'bg-slate-100 text-slate-600',
  PILOT: 'bg-cyan-100 text-cyan-700',
  DEV: 'bg-blue-100 text-blue-700',
  PROD: 'bg-emerald-100 text-emerald-700',
};

export default function StatusBadge({ status }: { status: string }) {
  const colors = colorMap[status] || 'bg-slate-100 text-slate-600';
  return (
    <span className={clsx('inline-block px-2 py-0.5 rounded-full text-xs font-medium', colors)}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}
