/**
 * Dashboard — what this deployment is currently connected to, and what you can
 * do about it.
 *
 * It used to be three static cards. A landing screen that shows no real state
 * tells a visitor nothing about whether the system is actually wired up, so
 * everything here is read live: the sources that are configured, how many notes
 * they hold, and what the current role is allowed to do with them.
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Database,
  FileUp,
  Plug,
  Shield,
  Table2,
} from 'lucide-react';
import { fetchDataSources } from '../api/dataSources';
import { fetchNotes } from '../api/notes';
import { loadResult, type SavedResult } from '../lib/resultStore';
import { useRole } from '../auth/RoleContext';
import type { DataSource } from '../types';
import { SkeletonBlock } from '../components/common/Skeleton';

interface Stat {
  label: string;
  value: string;
  hint?: string;
}

export default function Dashboard() {
  const { role, isAdmin, canExtract } = useRole();
  const [sources, setSources] = useState<DataSource[] | null>(null);
  const [noteCount, setNoteCount] = useState<number | null>(null);
  // Distinct from `noteCount === null`, which means "still loading". Without
  // this a failed request renders identically to a pending one, under a hint
  // claiming the number came from the default data source.
  const [noteCountFailed, setNoteCountFailed] = useState(false);
  const [lastResult, setLastResult] = useState<SavedResult | null>(null);

  useEffect(() => {
    setLastResult(loadResult());

    fetchDataSources()
      .then(setSources)
      .catch(() => setSources([]));

    if (canExtract) {
      // page_size=1 — we only want the total, not the page.
      fetchNotes(1, 1)
        .then((d) => setNoteCount(d.total))
        .catch(() => setNoteCountFailed(true));
    }
  }, [canExtract]);

  const stats: Stat[] = [
    {
      label: 'Data sources',
      value: sources === null ? '—' : String(sources.length),
      hint: sources?.length
        ? sources.map((s) => s.name).join(' · ')
        : 'None configured',
    },
    {
      label: 'Notes reachable',
      value: !canExtract
        ? 'n/a'
        : noteCountFailed
          ? 'Unavailable'
          : noteCount === null
            ? '—'
            : noteCount.toLocaleString(),
      hint: !canExtract
        ? 'Your role cannot read notes'
        : noteCountFailed
          ? 'Could not reach the data source'
          : 'In the default data source',
    },
    {
      label: 'Last extraction',
      value: lastResult ? `${lastResult.rows.length} rows` : 'None',
      hint: lastResult
        ? `${lastResult.columns.length} columns · this session`
        : 'Run one to see it here',
    },
    {
      label: 'Signed in as',
      value: role,
      hint: isAdmin ? 'Full access' : canExtract ? 'Extract only' : 'Read only',
    },
  ];

  const actions = [
    {
      to: '/database',
      icon: Database,
      title: 'Database Extractor',
      description:
        'Browse a connected clinical database, choose notes, and extract them into a table you define.',
      enabled: canExtract,
    },
    {
      to: '/upload',
      icon: FileUp,
      title: 'File Extractor',
      description: 'Upload .txt, .docx or .pdf documents and tabulate their contents.',
      enabled: canExtract,
    },
    {
      to: '/results',
      icon: Table2,
      title: 'Results',
      description: 'Review, correct and export the most recent extraction.',
      enabled: true,
    },
    {
      to: '/data-sources',
      icon: Plug,
      title: 'Data Sources',
      description:
        'Register a clinical database and map its columns. Configuration, not code.',
      enabled: isAdmin,
    },
  ].filter((a) => a.enabled);

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="page-title">MediExtractAI</h1>
        <p className="page-subtitle">
          Turn free-text clinical notes into structured, analysis-ready tables.
        </p>
      </div>

      {/* Live state */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-px bg-outline rounded-gm-lg overflow-hidden border border-outline">
        {stats.map((s) => (
          <div key={s.label} className="bg-surface px-4 py-3.5">
            <p className="text-label-sm text-on-surface-variant/80">{s.label}</p>
            <div className="text-headline-lg text-on-surface mt-1 tabular truncate">
              {sources === null && s.label === 'Data sources' ? (
                <SkeletonBlock className="h-6 w-12 mt-1" />
              ) : (
                s.value
              )}
            </div>
            {s.hint && (
              <p className="text-label-md text-on-surface-variant mt-1 truncate" title={s.hint}>
                {s.hint}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {actions.map(({ to, icon: Icon, title, description }) => (
          <Link
            key={to}
            to={to}
            className="card group px-4 py-3.5 hover:border-gm-blue/50 hover:bg-surface
                       transition-colors duration-150"
          >
            <div className="flex items-start gap-3">
              <span
                className="w-8 h-8 shrink-0 rounded-gm-md bg-surface-container border border-outline
                           flex items-center justify-center group-hover:bg-gm-blue-light
                           group-hover:border-gm-blue-surface transition-colors duration-150"
              >
                <Icon
                  size={16}
                  className="text-on-surface-variant group-hover:text-gm-blue transition-colors duration-150"
                />
              </span>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <h2 className="text-title-lg text-on-surface">{title}</h2>
                  <ArrowRight
                    size={14}
                    className="text-on-surface-variant opacity-0 -translate-x-1
                               group-hover:opacity-100 group-hover:translate-x-0
                               transition-all duration-150"
                  />
                </div>
                <p className="text-body-md text-on-surface-variant mt-0.5">{description}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Governance note */}
      <div className="card px-4 py-3.5 flex items-start gap-3">
        <span
          className="w-8 h-8 shrink-0 rounded-gm-md bg-gm-blue-light border border-gm-blue-surface
                     flex items-center justify-center"
        >
          <Shield size={15} className="text-gm-blue" />
        </span>
        <div>
          <h2 className="text-title-md text-on-surface">Synthetic data only</h2>
          <p className="text-body-md text-on-surface-variant mt-1">
            This demo has never processed real patient data. Authentication is disabled
            so the flows can be explored freely; the codebase carries OIDC token
            validation, role-based access control and an audit log that never stores note
            content, for deployment into a governed environment.
          </p>
        </div>
      </div>
    </div>
  );
}
