/**
 * DataSources — register and map the clinical databases this deployment reads.
 *
 * Administrator territory, and a one-off activity: connection details change
 * almost never, while clinicians extract every day. Keeping this off the daily
 * path is the whole reason it is a separate page rather than a form bolted to
 * the extractor.
 */

import { useCallback, useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Plug,
  Plus,
  ShieldAlert,
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
import EmptyState from '../components/common/EmptyState';

const EMPTY_MAPPING: ColumnMapping = {
  id: 'id',
  patient_id: 'patient_id',
  date: 'note_date',
  author: 'author',
  note_text: 'note_text',
  note_type: '',
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
  { key: 'id', label: 'Note ID', hint: 'Primary key of the note' },
  { key: 'patient_id', label: 'Patient ID', hint: 'MRN, NHS number, internal ID' },
  { key: 'date', label: 'Note date', hint: 'When it was written' },
  { key: 'author', label: 'Author', hint: 'Clinician who wrote it' },
  { key: 'note_text', label: 'Note text', hint: 'The free text we extract from' },
  {
    key: 'note_type',
    label: 'Note type (optional)',
    hint: 'Nursing, outpatient, specialty — leave blank if none',
  },
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
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
        ?.detail;
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
    if (!window.confirm(`Remove "${ds.name}"? The customer's database is untouched.`)) return;
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
      <span className="label">{label}</span>
      <input
        type={type}
        value={value ?? ''}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="input-field py-1.5"
      />
    </label>
  );

  return (
    <div className="max-w-5xl mx-auto space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="page-title">Data Sources</h1>
          <p className="page-subtitle">
            The clinical databases this deployment can read. Connection details stay on the
            server — clinicians only ever see the name.
          </p>
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="btn-filled shrink-0">
          {showForm ? <X size={14} /> : <Plus size={14} />}
          {showForm ? 'Cancel' : 'Add data source'}
        </button>
      </div>

      {/* Demo restriction */}
      <div className="card px-4 py-3 flex gap-2.5 items-start border-gm-yellow/30 bg-gm-yellow-light">
        <ShieldAlert size={16} className="text-gm-yellow mt-0.5 shrink-0" />
        <p className="text-body-md text-on-surface-variant">
          <span className="text-on-surface">Demo restriction.</span> This deployment runs
          without authentication, so a new data source may only point at an allow-listed host
          (<span className="mono">notes-db</span>). An unrestricted connection form on a
          public page would be an SSRF primitive and a credential-harvesting form in one. A
          real deployment authenticates its administrators and has no such limit.
        </p>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="panel">
          <div className="panel-header">
            <h2 className="text-title-lg text-on-surface">New data source</h2>
          </div>

          <div className="panel-body space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {field('Name', form.name, (v) => setForm({ ...form, name: v }), 'Trust EPR — Inpatient Notes')}
              {field('Description', form.description ?? '', (v) => setForm({ ...form, description: v }), 'Optional')}
            </div>

            <section>
              <h3 className="text-title-md text-on-surface mb-0.5">Connection</h3>
              <p className="text-label-md text-on-surface-variant mb-2.5">
                Stored server-side. The password is encrypted at rest and never returned by
                the API.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <label className="block">
                  <span className="label">Engine</span>
                  <select
                    value={form.engine}
                    onChange={(e) => setForm({ ...form, engine: e.target.value as DbEngine })}
                    className="select-field py-1.5"
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
            </section>

            <section>
              <h3 className="text-title-md text-on-surface mb-0.5">Schema mapping</h3>
              <p className="text-label-md text-on-surface-variant mb-2.5">
                No two systems name these the same way. Tell us which column means what and
                nothing else has to change.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {field('Table', form.table_name, (v) => setForm({ ...form, table_name: v }), 'medical_notes')}
                {MAPPING_FIELDS.map(({ key, label, hint }) => (
                  <label key={key} className="block">
                    <span className="label">{label}</span>
                    <input
                      value={form.columns[key]}
                      onChange={(e) =>
                        setForm({ ...form, columns: { ...form.columns, [key]: e.target.value } })
                      }
                      className="input-field py-1.5 font-mono"
                    />
                    <span className="hint">{hint}</span>
                  </label>
                ))}
              </div>
            </section>

            <div className="flex justify-end">
              <button
                onClick={handleCreate}
                disabled={saving || !form.name || !form.table_name}
                className="btn-filled"
              >
                {saving ? 'Saving…' : 'Add data source'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="card">
          <Loading message="Loading data sources…" />
        </div>
      ) : sources.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={Database}
            title="No data sources yet"
            description="Add one so clinicians can browse notes. Nothing else in the app has to change."
          />
        </div>
      ) : (
        <div className="space-y-3">
          {sources.map((ds) => {
            const result = results[ds.id];
            return (
              <div key={ds.id} className="panel">
                <div className="panel-header">
                  <div className="flex items-center gap-2 min-w-0">
                    <h2 className="text-title-lg text-on-surface truncate">{ds.name}</h2>
                    {ds.is_default && <span className="badge-info">default</span>}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => handleTest(ds.id)}
                      disabled={testing === ds.id}
                      className="btn-outlined py-1.5"
                    >
                      <Plug size={14} />
                      {testing === ds.id ? 'Testing…' : 'Test connection'}
                    </button>
                    <button
                      onClick={() => handleDelete(ds)}
                      className="btn-icon hover:text-gm-red"
                      title="Remove"
                      aria-label={`Remove ${ds.name}`}
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                <div className="panel-body space-y-3">
                  {ds.description && (
                    <p className="text-body-md text-on-surface-variant">{ds.description}</p>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-label-sm text-on-surface-variant/80 mb-1">Connection</p>
                      <p className="mono break-all">
                        {ds.engine}://{ds.username && `${ds.username}@`}
                        {ds.host}
                        {ds.port ? `:${ds.port}` : ''}/{ds.database_name}
                      </p>
                      <p className="text-label-md text-on-surface-variant mt-1">
                        Password {ds.has_password ? 'stored, encrypted' : 'not set'}
                      </p>
                    </div>

                    <div>
                      <p className="text-label-sm text-on-surface-variant/80 mb-1">
                        Schema mapping · <span className="mono">{ds.table_name}</span>
                      </p>
                      <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5">
                        {MAPPING_FIELDS.filter(
                          ({ key }) => key !== 'note_type' || ds.columns.note_type,
                        ).map(({ key, label }) => (
                          <div key={key} className="contents">
                            <dt className="text-label-md text-on-surface-variant whitespace-nowrap">
                              {label.replace(' (optional)', '')}
                            </dt>
                            <dd className="mono truncate">→ {ds.columns[key]}</dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  </div>

                  {result && (
                    <div
                      className={`rounded-gm-md border p-3 ${
                        result.ok
                          ? 'border-gm-green/25 bg-gm-green-light'
                          : 'border-gm-red/25 bg-gm-red-light'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        {result.ok ? (
                          <CheckCircle2 size={15} className="text-gm-green mt-0.5 shrink-0" />
                        ) : (
                          <AlertTriangle size={15} className="text-gm-red mt-0.5 shrink-0" />
                        )}
                        <p className="text-body-md text-on-surface">{result.message}</p>
                      </div>
                      {result.sample.length > 0 && (
                        <div className="mt-2.5 pl-[23px]">
                          <p className="text-label-md text-on-surface-variant mb-1">
                            Sample rows — check these really are notes:
                          </p>
                          <div className="space-y-0.5">
                            {result.sample.map((n) => (
                              <p key={n.id} className="mono text-on-surface-variant truncate">
                                {n.id} · {n.patient_id} · {n.date} ·{' '}
                                {n.text_preview.replace(/\s+/g, ' ').slice(0, 60)}…
                              </p>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
