import React from 'react';
import {
  Sparkles,
  Zap,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';

const STEPS = [
  {
    n: '1',
    title: 'Upload your resume',
    desc: 'Drop a PDF or DOCX on the Dashboard. We parse it instantly and build your profile.',
  },
  {
    n: '2',
    title: 'Paste a job description',
    desc: 'Head to New Analysis, paste any JD, and let the AI compare it against your resume.',
  },
  {
    n: '3',
    title: 'Review your match',
    desc: 'See your ATS score, match percentage, missing skills, and actionable recommendations.',
  },
  {
    n: '4',
    title: 'Download the report',
    desc: 'Generate a shareable PDF report or revisit any past analysis from your History.',
  },
];

export default function Home({ user, onNavigate }) {
  const firstName = user?.full_name?.trim().split(/\s+/)[0] || '';

  return (
    <div className="space-y-10">
      {/* Hero — personalized welcome */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-500 p-10 md:p-14 text-white shadow-xl">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.18),transparent_50%)] pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 h-64 w-64 rounded-full bg-white/10 blur-3xl pointer-events-none" />

        <div className="relative max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full bg-white/15 backdrop-blur px-3 py-1 text-xs font-medium ring-1 ring-white/20">
            <Sparkles className="h-3.5 w-3.5" />
            Your workspace
          </div>
          <h1 className="mt-4 text-4xl md:text-5xl font-bold leading-tight">
            Welcome{firstName ? `, ${firstName}` : ' back'}.
          </h1>
          <p className="mt-3 text-lg md:text-xl text-white/90 max-w-2xl">
            Analyze your resume against any job description and take one confident step closer to your next role.
          </p>

          <div className="mt-7 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate?.('analyze')}
              className="inline-flex items-center gap-2 rounded-lg bg-white text-indigo-700 px-5 py-2.5 text-sm font-semibold shadow-lg hover:bg-slate-100 transition"
            >
              <Zap className="h-4 w-4" />
              Start a New Analysis
            </button>
            <button
              onClick={() => onNavigate?.('dashboard')}
              className="inline-flex items-center gap-2 rounded-lg bg-white/10 backdrop-blur text-white ring-1 ring-white/30 px-5 py-2.5 text-sm font-semibold hover:bg-white/20 transition"
            >
              Go to Dashboard
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="glass-card p-8 md:p-10">
        <div className="mb-7">
          <div className="eyebrow mb-1">Workflow</div>
          <h2 className="h2">How it works</h2>
          <p className="subtle mt-1.5">
            From upload to insight in under a minute.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          {STEPS.map((s) => (
            <div
              key={s.n}
              className="relative rounded-xl bg-gradient-to-br from-slate-50 to-white ring-1 ring-slate-200 p-5"
            >
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-white font-bold text-sm shadow-md">
                {s.n}
              </div>
              <h4 className="mt-3 text-sm font-semibold text-slate-900">{s.title}</h4>
              <p className="mt-1 text-sm text-slate-600 leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Why ResuMatch */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-2xl bg-gradient-to-br from-indigo-50 to-purple-50 p-7 ring-1 ring-indigo-100">
          <h3 className="text-lg font-bold text-slate-900">Why ResuMatch AI?</h3>
          <ul className="mt-4 space-y-3 text-sm text-slate-700">
            {[
              'Beat applicant tracking systems with a verified ATS score',
              'Identify missing keywords before recruiters do',
              'Track every analysis in one organized history',
              'Persistent profile — your data stays with you across sessions',
            ].map((t) => (
              <li key={t} className="flex gap-2.5">
                <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-indigo-600" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="rounded-2xl bg-slate-900 p-7 text-slate-100 relative overflow-hidden">
          <div className="absolute -top-10 -right-10 h-40 w-40 rounded-full bg-indigo-500/30 blur-3xl pointer-events-none" />
          <h3 className="text-lg font-bold text-white">Ready to get started?</h3>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            Upload your resume to build your profile, then run analyses against any job description.
            Your dashboard always reflects your latest data.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate?.('dashboard')}
              className="inline-flex items-center gap-2 rounded-lg bg-white text-slate-900 px-4 py-2 text-sm font-semibold hover:bg-slate-100 transition"
            >
              Open Dashboard
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              onClick={() => onNavigate?.('history')}
              className="inline-flex items-center gap-2 rounded-lg bg-white/10 ring-1 ring-white/20 text-white px-4 py-2 text-sm font-semibold hover:bg-white/20 transition"
            >
              View History
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
