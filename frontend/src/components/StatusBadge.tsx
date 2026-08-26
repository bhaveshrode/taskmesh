'use client';

const statusColors: Record<string, string> = {
  pending: 'bg-slate-600 text-slate-200',
  queued: 'bg-blue-900 text-blue-300',
  running: 'bg-amber-900 text-amber-300',
  success: 'bg-emerald-900 text-emerald-300',
  failed: 'bg-red-900 text-red-300',
  cancelled: 'bg-slate-700 text-slate-400',
  retrying: 'bg-orange-900 text-orange-300',
  active: 'bg-emerald-900 text-emerald-300',
  stopped: 'bg-red-900 text-red-300',
};

const priorityColors: Record<string, string> = {
  low: 'bg-slate-700 text-slate-400',
  default: 'bg-blue-900 text-blue-300',
  high: 'bg-red-900 text-red-300',
};

export function StatusBadge({ status }: { status: string }) {
  const color = statusColors[status] || 'bg-slate-700 text-slate-300';
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {status}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: string }) {
  const color = priorityColors[priority] || 'bg-slate-700 text-slate-300';
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>
      {priority}
    </span>
  );
}
