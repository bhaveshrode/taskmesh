'use client';

import { useState } from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export default function CreateJobModal({ open, onClose, onCreated }: Props) {
  const [form, setForm] = useState({
    name: '',
    command: '',
    description: '',
    priority: 'default',
    queue_name: 'default',
    max_retries: 3,
    timeout_seconds: 300,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!open) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || 'Failed to create job');
      }
      onCreated();
      onClose();
      setForm({ name: '', command: '', description: '', priority: 'default', queue_name: 'default', max_retries: 3, timeout_seconds: 300 });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-xl bg-slate-800 border border-slate-700 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold mb-4">Create New Job</h2>

        {error && <div className="mb-4 rounded-lg bg-red-900/50 p-3 text-sm text-red-300">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              placeholder="My Job"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Command</label>
            <input
              type="text"
              required
              value={form.command}
              onChange={(e) => setForm({ ...form, command: e.target.value })}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white font-mono text-sm focus:border-brand-500 focus:outline-none"
              placeholder="echo hello || noop || http_request"
            />
            <p className="mt-1 text-xs text-slate-500">Use built-in tasks: noop, echo, transform, aggregate, delay, http_request</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Description</label>
            <input
              type="text"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              placeholder="Optional description"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="low">Low</option>
                <option value="default">Default</option>
                <option value="high">High</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Queue</label>
              <select
                value={form.queue_name}
                onChange={(e) => setForm({ ...form, queue_name: e.target.value })}
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              >
                <option value="default">Default</option>
                <option value="high">High</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Max Retries</label>
              <input
                type="number"
                min={0}
                max={10}
                value={form.max_retries}
                onChange={(e) => setForm({ ...form, max_retries: Number(e.target.value) })}
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Timeout (s)</label>
              <input
                type="number"
                min={10}
                max={3600}
                value={form.timeout_seconds}
                onChange={(e) => setForm({ ...form, timeout_seconds: Number(e.target.value) })}
                className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Job'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
