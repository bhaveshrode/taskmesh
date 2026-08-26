'use client';

import { useEffect, useState } from 'react';
import type { Workflow, WorkflowExecution } from '@/types';
import { StatusBadge } from '@/components/StatusBadge';
import { API_BASE } from '@/lib/api';

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selected, setSelected] = useState<Workflow | null>(null);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<Workflow | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/workflows`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        setWorkflows(await res.json());
      } catch { /* */ } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  useEffect(() => {
    if (selected) {
      fetch(`${API_BASE}/api/workflows/${selected.id}/executions`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      })
        .then((r) => r.json())
        .then(setExecutions)
        .catch(() => {});
    }
  }, [selected]);

  const handleRun = async (id: string) => {
    await fetch(`${API_BASE}/api/workflows/${id}/run`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    });
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this workflow?')) return;
    await fetch(`${API_BASE}/api/workflows/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
    });
    setWorkflows(workflows.filter((w) => w.id !== id));
    if (selected?.id === id) setSelected(null);
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workflows</h1>
          <p className="text-slate-400 mt-1">DAG-based multi-step workflows</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          + New Workflow
        </button>
      </div>

      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {workflows.length === 0 ? (
          <div className="col-span-full rounded-xl border border-slate-700 bg-slate-800 p-12 text-center text-slate-500">
            No workflows yet. Create one to chain jobs into a DAG!
          </div>
        ) : (
          workflows.map((wf) => {
            const taskCount = Object.keys(wf.dag_definition?.tasks || {}).length;
            return (
              <div
                key={wf.id}
                onClick={() => setSelected(wf)}
                className={`cursor-pointer rounded-xl border p-5 transition-all ${
                  selected?.id === wf.id
                    ? 'border-brand-500 bg-slate-800 ring-1 ring-brand-500'
                    : 'border-slate-700 bg-slate-800 hover:border-slate-600'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold">{wf.name}</h3>
                    {wf.description && (
                      <p className="text-sm text-slate-400 mt-1">{wf.description}</p>
                    )}
                  </div>
                  <StatusBadge status={wf.status} />
                </div>
                <div className="mt-4 flex items-center gap-4 text-sm text-slate-400">
                  <span>{taskCount} tasks</span>
                  <span>{wf.schedule_type}</span>
                </div>
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRun(wf.id); }}
                    className="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
                  >
                    ▶ Run
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); setEditing(wf); }}
                    className="rounded-lg bg-slate-600/30 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-600/50"
                  >
                    ✏️ Edit
                  </button>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(wf.id); }}
                    className="rounded-lg bg-red-600/20 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-600/40"
                  >
                    🗑 Delete
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Execution Details Panel */}
      {selected && (
        <div className="rounded-xl border border-slate-700 bg-slate-800 p-6">
          <h2 className="text-lg font-semibold mb-4">DAG: {selected.name}</h2>

          {/* DAG Visualization */}
          <div className="mb-6">
            <h3 className="text-sm font-medium text-slate-400 mb-3">Task Graph</h3>
            <div className="flex flex-wrap gap-3">
              {Object.entries(selected.dag_definition?.tasks || {}).map(([taskId, task]) => (
                <div
                  key={taskId}
                  className="rounded-lg border border-slate-600 bg-slate-900 p-3 min-w-[160px]"
                >
                  <div className="text-sm font-medium">{task.name || taskId}</div>
                  <div className="text-xs text-slate-500 font-mono mt-1">{task.command}</div>
                  {task.depends_on.length > 0 && (
                    <div className="text-xs text-slate-400 mt-2">
                      ← {task.depends_on.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Executions History */}
          <h3 className="text-sm font-medium text-slate-400 mb-3">Execution History</h3>
          {executions.length === 0 ? (
            <p className="text-sm text-slate-500">No executions yet</p>
          ) : (
            <div className="space-y-2">
              {executions.map((exec) => (
                <div key={exec.id} className="flex items-center justify-between rounded-lg border border-slate-600 bg-slate-900 p-3">
                  <div className="flex items-center gap-3">
                    <StatusBadge status={exec.status} />
                    <span className="text-xs text-slate-400">
                      {new Date(exec.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {Object.entries(exec.task_states || {}).map(([taskId, state]) => (
                      <span
                        key={taskId}
                        className={`rounded px-2 py-0.5 text-xs ${
                          state.status === 'success'
                            ? 'bg-emerald-900 text-emerald-300'
                            : state.status === 'failed'
                            ? 'bg-red-900 text-red-300'
                            : state.status === 'running'
                            ? 'bg-amber-900 text-amber-300'
                            : 'bg-slate-700 text-slate-400'
                        }`}
                      >
                        {taskId}: {state.status}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create Workflow Modal */}
      {showCreate && (
        <CreateWorkflowModal
          onClose={() => setShowCreate(false)}
          onCreated={() => { setShowCreate(false); window.location.reload(); }}
        />
      )}

      {/* Edit Workflow Modal */}
      {editing && (
        <EditWorkflowModal
          workflow={editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); window.location.reload(); }}
        />
      )}
    </div>
  );
}

function CreateWorkflowModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [form, setForm] = useState({
    name: '',
    description: '',
    tasks: [
      { id: 'task_1', name: 'Task 1', command: 'echo', depends_on: [] as string[] },
    ],
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const addTask = () => {
    const n = form.tasks.length + 1;
    setForm({
      ...form,
      tasks: [...form.tasks, { id: `task_${n}`, name: `Task ${n}`, command: 'echo', depends_on: [] }],
    });
  };

  const updateTask = (idx: number, field: string, value: string | string[]) => {
    const tasks = [...form.tasks];
    (tasks[idx] as Record<string, unknown>)[field] = value;
    setForm({ ...form, tasks });
  };

  const removeTask = (idx: number) => {
    setForm({ ...form, tasks: form.tasks.filter((_, i) => i !== idx) });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/workflows`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || 'Failed');
      }
      onCreated();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error');
    } finally {
      setLoading(false);
    }
  };

  const otherTaskIds = (currentIdx: number) =>
    form.tasks.filter((_, i) => i !== currentIdx).map((t) => t.id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-xl bg-slate-800 border border-slate-700 p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-xl font-semibold mb-4">Create Workflow</h2>
        {error && <div className="mb-4 rounded-lg bg-red-900/50 p-3 text-sm text-red-300">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
            <input
              type="text" required value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Description</label>
            <input
              type="text" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-300">Tasks</label>
              <button type="button" onClick={addTask} className="rounded-lg bg-brand-600/20 px-3 py-1 text-xs font-medium text-brand-400 hover:bg-brand-600/40">+ Add Task</button>
            </div>
            <div className="space-y-3">
              {form.tasks.map((task, idx) => (
                <div key={idx} className="rounded-lg border border-slate-600 bg-slate-900 p-3 space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <input
                      placeholder="Task ID" value={task.id}
                      onChange={(e) => updateTask(idx, 'id', e.target.value)}
                      className="rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-white focus:outline-none"
                    />
                    <input
                      placeholder="Name" value={task.name}
                      onChange={(e) => updateTask(idx, 'name', e.target.value)}
                      className="rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-white focus:outline-none"
                    />
                    <div className="flex gap-1">
                      <input
                        placeholder="Command" value={task.command}
                        onChange={(e) => updateTask(idx, 'command', e.target.value)}
                        className="flex-1 rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-white font-mono focus:outline-none"
                      />
                      {form.tasks.length > 1 && (
                        <button type="button" onClick={() => removeTask(idx)} className="rounded bg-red-900/50 px-2 py-1 text-xs text-red-400 hover:bg-red-900 hover:text-red-300">✕ Remove</button>
                      )}
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-slate-500">Depends on:</label>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {otherTaskIds(idx).map((depId) => (
                        <button
                          key={depId} type="button"
                          onClick={() => {
                            const deps = task.depends_on.includes(depId)
                              ? task.depends_on.filter((d) => d !== depId)
                              : [...task.depends_on, depId];
                            updateTask(idx, 'depends_on', deps);
                          }}
                          className={`rounded px-2 py-0.5 text-xs ${
                            task.depends_on.includes(depId)
                              ? 'bg-brand-600 text-white'
                              : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                          }`}
                        >
                          {depId}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700">Cancel</button>
            <button type="submit" disabled={loading} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
              {loading ? 'Creating...' : 'Create Workflow'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditWorkflowModal({ workflow, onClose, onSaved }: { workflow: Workflow; onClose: () => void; onSaved: () => void }) {
  const tasks = Object.entries(workflow.dag_definition?.tasks || {}).map(([id, t]: [string, any]) => ({
    id,
    name: t.name || id,
    command: t.command,
    depends_on: t.depends_on || [],
    payload: t.payload || {},
    max_retries: t.max_retries || 3,
    timeout_seconds: t.timeout_seconds || 300,
  }));
  const [form, setForm] = useState({ name: workflow.name, description: workflow.description || '', tasks });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const addTask = () => {
    const n = form.tasks.length + 1;
    setForm({ ...form, tasks: [...form.tasks, { id: `task_${n}`, name: `Task ${n}`, command: 'echo', depends_on: [], payload: {}, max_retries: 3, timeout_seconds: 300 }] });
  };

  const updateTask = (idx: number, field: string, value: string | string[]) => {
    const newTasks = [...form.tasks];
    (newTasks[idx] as Record<string, unknown>)[field] = value;
    setForm({ ...form, tasks: newTasks });
  };

  const removeTask = (idx: number) => {
    setForm({ ...form, tasks: form.tasks.filter((_: any, i: number) => i !== idx) });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/workflows/${workflow.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('token')}` },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const body = await res.json();
        throw new Error(body.detail || 'Failed');
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error');
    } finally {
      setLoading(false);
    }
  };

  const otherTaskIds = (currentIdx: number) => form.tasks.filter((_: any, i: number) => i !== currentIdx).map((t: any) => t.id);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-xl bg-slate-800 border border-slate-700 p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-xl font-semibold mb-4">Edit Workflow</h2>
        {error && <div className="mb-4 rounded-lg bg-red-900/50 p-3 text-sm text-red-300">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
            <input type="text" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Description</label>
            <input type="text" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="w-full rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-white focus:border-brand-500 focus:outline-none" />
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-300">Tasks</label>
              <button type="button" onClick={addTask} className="rounded-lg bg-brand-600/20 px-3 py-1 text-xs font-medium text-brand-400 hover:bg-brand-600/40">+ Add Task</button>
            </div>
            <div className="space-y-3">
              {form.tasks.map((task: any, idx: number) => (
                <div key={idx} className="rounded-lg border border-slate-600 bg-slate-900 p-3 space-y-2">
                  <div className="grid grid-cols-3 gap-2">
                    <input placeholder="Task ID" value={task.id} onChange={(e) => updateTask(idx, 'id', e.target.value)} className="rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-white focus:outline-none" />
                    <input placeholder="Name" value={task.name} onChange={(e) => updateTask(idx, 'name', e.target.value)} className="rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-white focus:outline-none" />
                    <div className="flex gap-1">
                      <input placeholder="Command" value={task.command} onChange={(e) => updateTask(idx, 'command', e.target.value)} className="flex-1 rounded border border-slate-600 bg-slate-800 px-2 py-1.5 text-xs text-white font-mono focus:outline-none" />
                      {form.tasks.length > 1 && (
                        <button type="button" onClick={() => removeTask(idx)} className="rounded bg-red-900/50 px-2 py-1 text-xs text-red-400 hover:bg-red-900 hover:text-red-300">✕ Remove</button>
                      )}
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-slate-500">Depends on:</label>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {otherTaskIds(idx).map((depId: string) => (
                        <button key={depId} type="button" onClick={() => {
                          const deps = task.depends_on.includes(depId) ? task.depends_on.filter((d: string) => d !== depId) : [...task.depends_on, depId];
                          updateTask(idx, 'depends_on', deps);
                        }} className={`rounded px-2 py-0.5 text-xs ${task.depends_on.includes(depId) ? 'bg-brand-600 text-white' : 'bg-slate-700 text-slate-400 hover:bg-slate-600'}`}>{depId}</button>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700">Cancel</button>
            <button type="submit" disabled={loading} className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50">
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
