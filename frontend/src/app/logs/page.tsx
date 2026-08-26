'use client';

import { useEffect, useState } from 'react';
import type { Job, LogEntry } from '@/types';

const levelColors: Record<string, string> = {
  info: 'text-blue-400',
  warn: 'text-amber-400',
  warning: 'text-amber-400',
  error: 'text-red-400',
  debug: 'text-slate-400',
};

export default function LogsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch('/api/jobs?page_size=50', {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        const data = await res.json();
        setJobs(data.jobs || []);
        if (!selectedJobId && data.jobs?.length > 0) {
          setSelectedJobId(data.jobs[0].id);
        }
      } catch { /* */ } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (selectedJobId) {
      fetch(`/api/jobs/${selectedJobId}/logs?limit=200`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
        .then((r) => r.json())
        .then(setLogs)
        .catch(() => setLogs([]));
    }
  }, [selectedJobId]);

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
        <h1 className="text-2xl font-bold">Logs</h1>
        <p className="text-slate-400 mt-1">View execution logs for jobs</p>
      </div>

      <div className="flex gap-4 h-[calc(100vh-12rem)]">
        {/* Job list */}
        <div className="w-72 rounded-xl border border-slate-700 bg-slate-800 overflow-y-auto flex-shrink-0">
          <div className="sticky top-0 border-b border-slate-700 bg-slate-900 px-4 py-3">
            <h3 className="text-sm font-medium text-slate-400">Jobs</h3>
          </div>
          <div className="divide-y divide-slate-700">
            {jobs.map((job) => (
              <button
                key={job.id}
                onClick={() => setSelectedJobId(job.id)}
                className={`w-full px-4 py-3 text-left text-sm transition-colors ${
                  selectedJobId === job.id
                    ? 'bg-brand-600/20 border-l-2 border-brand-500'
                    : 'hover:bg-slate-750'
                }`}
              >
                <div className="font-medium truncate">{job.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">{job.status}</div>
              </button>
            ))}
            {jobs.length === 0 && (
              <div className="px-4 py-8 text-center text-sm text-slate-500">No jobs</div>
            )}
          </div>
        </div>

        {/* Log viewer */}
        <div className="flex-1 rounded-xl border border-slate-700 bg-slate-900 overflow-hidden flex flex-col">
          <div className="border-b border-slate-700 px-4 py-3 flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-400">
              {selectedJobId ? `Job: ${selectedJobId.slice(0, 8)}...` : 'Select a job'}
            </h3>
            {logs.length > 0 && (
              <span className="text-xs text-slate-500">{logs.length} entries</span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-4 font-mono text-sm">
            {logs.length === 0 ? (
              <div className="text-slate-500 text-center py-8">No logs for this job</div>
            ) : (
              <div className="space-y-1">
                {logs.map((log) => (
                  <div key={log.id} className="flex gap-3 hover:bg-slate-800 rounded px-2 py-1">
                    <span className="text-xs text-slate-600 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`text-xs font-bold uppercase w-14 ${levelColors[log.level] || 'text-slate-400'}`}>
                      {log.level}
                    </span>
                    <span className="text-sm text-slate-300 break-all">{log.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
