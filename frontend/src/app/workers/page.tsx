'use client';

import { useEffect, useState } from 'react';
import type { Worker } from '@/types';
import { StatusBadge } from '@/components/StatusBadge';
import { deleteWorker, reactivateWorker } from '@/lib/api';

export default function WorkersPage() {
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [loading, setLoading] = useState(true);

  const loadWorkers = async () => {
    try {
      const res = await fetch('/api/workers', {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setWorkers(await res.json());
    } catch { /* */ } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkers();
    const interval = setInterval(loadWorkers, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this worker record?')) return;
    try {
      await deleteWorker(id);
      await loadWorkers();
    } catch (err) {
      alert('Failed to delete worker');
    }
  };

  const handleReactivate = async (id: string) => {
    try {
      await reactivateWorker(id);
      await loadWorkers();
    } catch (err) {
      alert('Failed to reactivate worker');
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Workers</h1>
        <p className="text-slate-400 mt-1">Monitor active worker processes</p>
      </div>

      {workers.length === 0 ? (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-12 text-center text-slate-500">
          <div className="text-4xl mb-3">🖥️</div>
          <p>No workers online</p>
          <p className="text-sm mt-1">Start workers with: <code className="text-brand-400">python -m app.worker</code></p>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {workers.map((worker) => (
            <div key={worker.id} className="rounded-xl border border-slate-700 bg-slate-800 p-5">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="font-semibold text-lg">{worker.id}</h3>
                  <p className="text-sm text-slate-400">
                    {worker.hostname} (PID: {worker.pid})
                  </p>
                </div>
                <StatusBadge status={worker.status} />
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Queues:</span>
                  <div className="flex gap-1 mt-1">
                    {worker.queues.map((q) => (
                      <span key={q} className="rounded bg-slate-700 px-2 py-0.5 text-xs">{q}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Concurrency:</span>
                  <p className="text-white mt-1">
                    {worker.current_jobs.length} / {worker.max_concurrent}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500">Completed:</span>
                  <p className="text-emerald-400 mt-1">{worker.jobs_completed}</p>
                </div>
                <div>
                  <span className="text-slate-500">Failed:</span>
                  <p className="text-red-400 mt-1">{worker.jobs_failed}</p>
                </div>
              </div>

              <div className="mt-4 border-t border-slate-700 pt-3">
                <span className="text-xs text-slate-500">
                  Heartbeat: {worker.heartbeat_at ? new Date(worker.heartbeat_at).toLocaleString() : 'Never'}
                </span>
              </div>

              {worker.status === 'stopped' && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => handleReactivate(worker.id)}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500"
                  >
                    ▶ Reactivate
                  </button>
                  <button
                    onClick={() => handleDelete(worker.id)}
                    className="rounded-lg bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-500"
                  >
                    🗑 Delete
                  </button>
                </div>
              )}

              {worker.current_jobs.length > 0 && (
                <div className="mt-3">
                  <span className="text-xs text-slate-500">Active Jobs:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {worker.current_jobs.map((jId) => (
                      <span key={jId} className="rounded bg-amber-900/50 px-2 py-0.5 text-xs text-amber-300 font-mono">
                        {jId.slice(0, 8)}...
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
