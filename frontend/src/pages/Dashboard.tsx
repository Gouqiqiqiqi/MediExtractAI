/**
 * Dashboard — home page with Google-style action cards and summary.
 */

import { Link } from 'react-router-dom';
import { Database, FileUp, Table2, Shield, ArrowRight } from 'lucide-react';

const actions = [
  {
    to: '/database',
    icon: Database,
    title: 'Database Extractor',
    description: 'Connect to your medical notes database and extract structured data from free-text records.',
    colour: 'bg-gm-blue',
    lightColour: 'bg-gm-blue-light',
    textColour: 'text-gm-blue',
  },
  {
    to: '/upload',
    icon: FileUp,
    title: 'File Extractor',
    description: 'Upload .txt, .doc, or .pdf medical documents and tabulate their contents.',
    colour: 'bg-gm-green',
    lightColour: 'bg-green-50',
    textColour: 'text-gm-green',
  },
  {
    to: '/results',
    icon: Table2,
    title: 'View Results',
    description: 'Review, edit, and export your most recent extraction results.',
    colour: 'bg-gm-yellow',
    lightColour: 'bg-yellow-50',
    textColour: 'text-gm-yellow',
  },
];

export default function Dashboard() {
  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-display-sm font-bold text-on-surface">
          Welcome to MediExtractAI
        </h1>
        <p className="text-body-lg text-on-surface-variant mt-2">
          AI-powered medical note extraction — turn free text into structured, exportable data.
        </p>
      </div>

      {/* Action cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
        {actions.map(({ to, icon: Icon, title, description, lightColour, textColour }) => (
          <Link
            key={to}
            to={to}
            className="card-elevated group hover:translate-y-[-2px] transition-all duration-200"
          >
            <div className={`w-12 h-12 ${lightColour} rounded-gm-lg flex items-center justify-center mb-4
                            group-hover:scale-105 transition-transform duration-200`}>
              <Icon size={24} className={textColour} />
            </div>
            <h3 className="text-title-md font-semibold text-on-surface mb-1.5">
              {title}
            </h3>
            <p className="text-body-md text-on-surface-variant mb-4">{description}</p>
            <div className={`flex items-center gap-1 ${textColour} text-label-lg font-medium`}>
              Get started <ArrowRight size={16} />
            </div>
          </Link>
        ))}
      </div>

      {/* Security banner */}
      <div className="card-elevated flex items-start gap-4 bg-surface">
        <div className="w-10 h-10 rounded-gm-lg bg-gm-blue-light flex items-center justify-center flex-shrink-0 mt-0.5">
          <Shield size={20} className="text-gm-blue" />
        </div>
        <div>
          <h3 className="text-title-sm font-semibold text-on-surface mb-1">Privacy by Design</h3>
          <p className="text-body-md text-on-surface-variant">
            This demo runs on synthetic clinical notes only — no real patient data.
            The architecture supports OIDC authentication, role-based access, and full
            audit logging when deployed in a governed environment.
          </p>
        </div>
      </div>
    </div>
  );
}
