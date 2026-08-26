'use client';

import { useEffect, useState } from 'react';
import type { DashboardStats, Job } from '@/types';
import { StatusBadge } from '@/components/StatusBadge';

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: string; color: string }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-800 p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-slate-400">{label}</p>
          <p className={`mt-1 text-3xl font-bold ${color}`}>{value}</p>
        </div>
        <span className="text-3xl">{icon}</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, j] = await Promise.all([
          fetch('/api/dashboard/stats', {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          }).then((r) => r.json()),
          fetch('/api/jobs?page_size=10', {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          }).then((r) => r.json()),
        ]);
        setStats(s);
        setRecentJobs(j.jobs || []);
      } catch {
        // API not available
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-slate-400 mt-1">Overview of your job platform</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Total Jobs" value={stats?.total_jobs || 0} icon="⚡" color="text-white" />
        <StatCard label="Running" value={stats?.running_jobs || 0} icon="🔄" color="text-amber-400" />
        <StatCard label="Completed" value={stats?.completed_jobs || 0} icon="✅" color="text-emerald-400" />
        <StatCard label="Failed" value={stats?.failed_jobs || 0} icon="❌" color="text-red-400" />
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Queued" value={stats?.queued_jobs || 0} icon="📋" color="text-blue-400" />
        <StatCard label="Workflows" value={stats?.total_workflows || 0} icon="🔀" color="text-purple-400" />
        <StatCard label="Active Workers" value={stats?.active_workers || 0} icon="🖥️" color="text-emerald-400" />
        <StatCard label="Last 24h" value={stats?.jobs_last_24h || 0} icon="📈" color="text-cyan-400" />
      </div>

      {/* Recent Jobs */}
      <div className="rounded-xl border border-slate-700 bg-slate-800">
        <div className="border-b border-slate-700 px-6 py-4">
          <h2 className="text-lg font-semibold">Recent Jobs</h2>
        </div>
        <div className="divide-y divide-slate-700">
          {recentJobs.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-500">
              No jobs yet. Create one to get started!
            </div>
          ) : (
            recentJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between px-6 py-3 hover:bg-slate-750">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="font-medium">{job.name}</p>
                    <p className="text-sm text-slate-400 font-mono">{job.command}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <StatusBadge status={job.status} />
                  <span className="text-xs text-slate-500">
                    {new Date(job.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
