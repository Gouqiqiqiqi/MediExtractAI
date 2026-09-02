/**
 * DataSources — register and map the customer databases this deployment reads.
 *
 * Administrator territory, and a one-off activity: connection details change
 * almost never, while clinicians extract every day. Keeping this off the daily
 * path is the whole reason it is a separate page rather than a form on the
 * extractor.
 */

import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Plug,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
import type {
  ColumnMapping,
  DataSource,
  DataSourceCreate,
  DataSourceTestResult,
  DbEngine,
} from '../types';
import {
  createDataSource,
  deleteDataSource,
  fetchDataSources,
  testDataSource,
} from '../api/dataSources';
import Loading from '../components/common/Loading';

const EMPTY_MAPPING: ColumnMapping = {
  id: 'id',
  patient_id: 'patient_id',
  date: 'note_date',
  author: 'author',
  note_text: 'note_text',
};

const EMPTY_FORM: DataSourceCreate = {
  name: '',
  description: '',
  engine: 'postgresql',
  host: '',
  port: 5432,
  database_name: '',
  username: '',
  password: '',
  table_name: '',
  columns: { ...EMPTY_MAPPING },
};

const MAPPING_FIELDS: { key: keyof ColumnMapping; label: string; hint: string }[] = [
  { key: 'id', label: 'Note ID', hint: 'Primary key — identifies the note' },
  { key: 'patient_id', label: 'Patient ID', hint: 'MRN, NHS number, internal ID' },
  { key: 'date', label: 'Note date', hint: 'When the note was written' },
  { key: 'author', label: 'Author', hint: 'Clinician who wrote it' },
  { key: 'note_text', label: 'Note text', hint: 'The free text we extract from' },
];

export default function DataSources() {
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<DataSourceCreate>({ ...EMPTY_FORM });
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, DataSourceTestResult>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setSources(await fetchDataSources());
    } catch {
      toast.error('Could not load data sources');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    setSaving(true);
    try {
      await createDataSource(form);
      toast.success('Data source added');
      setShowForm(false);
      setForm({ ...EMPTY_FORM, columns: { ...EMPTY_MAPPING } });
      await load();
    } catch (err) {
      const detail =
        (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Could not add data source');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async (id: string) => {
    setTesting(id);
    try {
      const result = await testDataSource(id);
      setResults((prev) => ({ ...prev, [id]: result }));
      if (result.ok) toast.success(`Connected — ${result.note_count} notes`);
      else toast.error('Connection failed');
    } catch {
      toast.error('Test request failed');
    } finally {
      setTesting(null);
    }
  };

  const handleDelete = async (ds: DataSource) => {
    if (!window.confirm(`Remove "${ds.name}"? The customer's database is untouched.`)) {
      return;
    }
    try {
      await deleteDataSource(ds.id);
      toast.success('Data source removed');
      await load();
    } catch {
      toast.error('Could not remove data source');
    }
  };

  const field = (
    label: string,
    value: string | number | null,
    onChange: (v: string) => void,
    placeholder = '',
    type = 'text',
  ) => (
    <label className="block">
      <span className="block text-label-md text-on-surface-variant mb-1">{label}</span>
      <input
        type={type}
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2 bg-surface-container rounded-gm-lg text-body-md
                   text-on-surface border-0 focus:outline-none focus:ring-2 focus:ring-gm-blue/40"
      />
    </label>
  );

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-display-sm font-bold text-on-surface">Data Sources</h1>
          <p className="text-body-md text-on-surface-variant mt-1">
            The clinical databases this deployment can read. Connection details stay on
            the server — clinicians only ever see the name.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="btn-filled flex items-center gap-2 text-label-lg shrink-0"
        >
          {showForm ? <X size={18} /> : <Plus size={18} />}
          {showForm ? 'Cancel' : 'Add data source'}
        </button>
      </div>

      {/* Demo restriction notice */}
      <div className="card-elevated flex gap-3 items-start bg-gm-yellow-light/40">
        <AlertTriangle size={18} className="text-gm-yellow mt-0.5 shrink-0" />
        <p className="text-body-md text-on-surface-variant">
          <span className="font-medium text-on-surface">Demo restriction.</span>{' '}
          This deployment runs without authentication, so new data sources may only point
          at an allow-listed host (<code>notes-db</code>). An unrestricted connection form
          on a public page would be an SSRF primitive and a credential-harvesting form in
          one. A real deployment authenticates its administrators and has no such limit.
        </p>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card-elevated space-y-5">
          <h2 className="text-title-md font-medium text-on-surface">New data source</h2>

          <div className="grid grid-cols-2 gap-4">
            {field('Name', form.name, (v) => setForm({ ...form, name: v }), 'Trust EPR — Inpatient Notes')}
            {field('Description', form.description ?? '', (v) => setForm({ ...form, description: v }), 'Optional')}
          </div>

          <div>
            <h3 className="text-label-lg font-medium text-on-surface mb-2">Connection</h3>
            <div className="grid grid-cols-3 gap-4">
              <label className="block">
                <span className="block text-label-md text-on-surface-variant mb-1">Engine</span>
                <select
                  value={form.engine}
                  onChange={(e) => setForm({ ...form, engine: e.target.value as DbEngine })}
                  className="w-full px-3 py-2 bg-surface-container rounded-gm-lg text-body-md
                             text-on-surface border-0 focus:outline-none focus:ring-2 focus:ring-gm-blue/40"
                >
                  <option value="postgresql">PostgreSQL</option>
                  <option value="mssql">SQL Server</option>
                  <option value="sqlite">SQLite</option>
                </select>
              </label>
              {field('Host', form.host, (v) => setForm({ ...form, host: v }), 'notes-db')}
              {field('Port', form.port ?? '', (v) => setForm({ ...form, port: v ? Number(v) : null }), '5432', 'number')}
              {field('Database', form.database_name, (v) => setForm({ ...form, database_name: v }), 'clinical_notes')}
              {field('Username', form.username, (v) => setForm({ ...form, username: v }))}
              {field('Password', form.password, (v) => setForm({ ...form, password: v }), '', 'password')}
            </div>
          </div>

          <div>
            <h3 className="text-label-lg font-medium text-on-surface mb-1">Schema mapping</h3>
            <p className="text-label-md text-on-surface-variant mb-3">
              No two systems name these the same way. Tell us which column means what and
              nothing else has to change.
            </p>
            <div className="grid grid-cols-3 gap-4">
              {field('Table', form.table_name, (v) => setForm({ ...form, table_name: v }), 'medical_notes')}
              {MAPPING_FIELDS.map(({ key, label, hint }) => (
                <label key={key} className="block">
                  <span className="block text-label-md text-on-surface-variant mb-1">
                    {label}
                  </span>
                  <input
                    value={form.columns[key]}
                    placeholder={hint}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        columns: { ...form.columns, [key]: e.target.value },
                      })
                    }
                    className="w-full px-3 py-2 bg-surface-container rounded-gm-lg text-body-md
                               text-on-surface border-0 focus:outline-none focus:ring-2 focus:ring-gm-blue/40"
                  />
                  <span className="block text-label-md text-on-surface-variant mt-1">{hint}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleCreate}
              disabled={saving || !form.name || !form.table_name}
              className="btn-filled text-label-lg disabled:opacity-40"
            >
              {saving ? 'Saving…' : 'Add data source'}
            </button>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <Loading />
      ) : sources.length === 0 ? (
        <div className="card-elevated text-center py-12">
          <Database size={32} className="mx-auto text-on-surface-variant mb-3" />
          <p className="text-body-md text-on-surface-variant">
            No data sources yet. Add one to let clinicians browse notes.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {sources.map((ds) => {
            const result = results[ds.id];
            return (
              <div key={ds.id} className="card-elevated space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-title-md font-medium text-on-surface">{ds.name}</span>
                      {ds.is_default && (
                        <span className="px-2 py-0.5 rounded-gm-lg bg-gm-blue-light text-gm-blue text-label-md">
                          default
                        </span>
                      )}
                    </div>
                    {ds.description && (
                      <p className="text-body-md text-on-surface-variant mt-1">{ds.description}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleTest(ds.id)}
                      disabled={testing === ds.id}
                      className="btn-outlined flex items-center gap-2 text-label-md disabled:opacity-40"
                    >
                      <Plug size={16} />
                      {testing === ds.id ? 'Testing…' : 'Test connection'}
                    </button>
                    <button
                      onClick={() => handleDelete(ds)}
                      className="w-9 h-9 rounded-gm-xl flex items-center justify-center
                                 text-on-surface-variant hover:bg-surface-container transition-colors"
                      title="Remove"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 text-label-md">
                  <div>
                    <span className="text-on-surface-variant">Connection</span>
                    <div className="font-mono text-on-surface mt-1">
                      {ds.engine}://{ds.username && `${ds.username}@`}
                      {ds.host}
                      {ds.port ? `:${ds.port}` : ''}/{ds.database_name}
                    </div>
                    <div className="text-on-surface-variant mt-0.5">
                      Password {ds.has_password ? 'stored (encrypted)' : 'not set'}
                    </div>
                  </div>
                  <div>
                    <span className="text-on-surface-variant">
                      Schema mapping · <span className="font-mono">{ds.table_name}</span>
                    </span>
                    <div className="font-mono text-on-surface mt-1 space-y-0.5">
                      {MAPPING_FIELDS.map(({ key, label }) => (
                        <div key={key}>
                          {label} → {ds.columns[key]}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {result && (
                  <div
                    className={`rounded-gm-lg p-3 text-label-md ${
                      result.ok ? 'bg-gm-green-light/40' : 'bg-gm-red-light/40'
                    }`}
                  >
                    <div className="flex items-center gap-2 font-medium text-on-surface">
                      {result.ok ? (
                        <CheckCircle2 size={16} className="text-gm-green" />
                      ) : (
                        <AlertTriangle size={16} className="text-gm-red" />
                      )}
                      {result.message}
                    </div>
                    {result.sample.length > 0 && (
                      <div className="mt-2 space-y-1">
                        <span className="text-on-surface-variant">
                          Sample rows — check these really are notes:
                        </span>
                        {result.sample.map((n) => (
                          <div key={n.id} className="font-mono text-on-surface truncate">
                            {n.id} · {n.patient_id} · {n.date} · {n.text_preview.slice(0, 70)}…
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
