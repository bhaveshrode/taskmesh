'use client';

import { useEffect, useState, useCallback } from 'react';
import type { Job, JobListResponse } from '@/types';
import { StatusBadge, PriorityBadge } from '@/components/StatusBadge';
import CreateJobModal from '@/components/CreateJobModal';
import { API_BASE } from '@/lib/api';

export default function JobsPage() {
  const [data, setData] = useState<JobListResponse | null>(null);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchJobs = useCallback(async () => {
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' });
      if (statusFilter) params.set('status', statusFilter);
      if (search) params.set('search', search);
      const res = await fetch(`${API_BASE}/api/jobs?${params}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setData(await res.json());
    } catch {
      // API unavailable
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, search]);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleAction = async (jobId: string, action: 'run' | 'cancel' | 'delete') => {
    const method = action === 'delete' ? 'DELETE' : 'POST';
    const url = action === 'delete' ? `${API_BASE}/api/jobs/${jobId}` : `${API_BASE}/api/jobs/${jobId}/${action}`;
    await fetch(url, {
      method,
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    });
    fetchJobs();
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Jobs</h1>
          <p className="text-slate-400 mt-1">Manage and monitor your jobs</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + New Job
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search jobs..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:border-brand-500 focus:outline-none w-64"
        />
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-white focus:border-brand-500 focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
          <option value="retrying">Retrying</option>
        </select>
      </div>

      {/* Jobs Table */}
      <div className="rounded-xl border border-slate-700 bg-slate-800 overflow-hidden">
        {loading ? (
          <div className="flex h-64 items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-slate-900 border-b border-slate-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Name</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Command</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Priority</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Attempts</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Worker</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-400 uppercase">Created</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-400 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {(!data?.jobs || data.jobs.length === 0) ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-slate-500">No jobs found</td>
                </tr>
              ) : (
                data.jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-750">
                    <td className="px-4 py-3">
                      <div className="font-medium text-sm">{job.name}</div>
                      {job.description && (
                        <div className="text-xs text-slate-500 mt-0.5">{job.description}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-slate-300 max-w-[200px] truncate">{job.command}</td>
                    <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                    <td className="px-4 py-3"><PriorityBadge priority={job.priority} /></td>
                    <td className="px-4 py-3 text-sm text-slate-300">{job.attempt}/{job.max_retries}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{job.worker_id || '—'}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{new Date(job.created_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        {job.status !== 'running' && job.status !== 'success' && (
                          <button
                            onClick={() => handleAction(job.id, 'run')}
                            className="rounded px-2 py-1 text-xs text-emerald-400 hover:bg-emerald-900/50"
                          >
                            Run
                          </button>
                        )}
                        {job.status === 'running' && (
                          <button
                            onClick={() => handleAction(job.id, 'cancel')}
                            className="rounded px-2 py-1 text-xs text-amber-400 hover:bg-amber-900/50"
                          >
                            Cancel
                          </button>
                        )}
                        <button
                          onClick={() => handleAction(job.id, 'delete')}
                          className="rounded px-2 py-1 text-xs text-red-400 hover:bg-red-900/50"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}

        {/* Pagination */}
        {data && data.total > 20 && (
          <div className="flex items-center justify-between border-t border-slate-700 px-4 py-3">
            <span className="text-sm text-slate-400">
              Showing {(page - 1) * 20 + 1}-{Math.min(page * 20, data.total)} of {data.total}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="rounded px-3 py-1 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={page * 20 >= data.total}
                className="rounded px-3 py-1 text-sm text-slate-300 hover:bg-slate-700 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      <CreateJobModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={fetchJobs}
      />
    </div>
  );
}
