import React, { useState } from 'react';
import {
  Upload,
  FileText,
  Briefcase,
  Sparkles,
  Loader2,
  Download,
  CheckCircle2,
  XCircle,
  TrendingUp,
  PartyPopper,
  ThumbsUp,
  AlertTriangle,
  Target,
  ArrowRight,
  Trophy,
  FileSearch,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  Card,
  CardHeader,
  ScoreCard,
  ProgressBar,
  EmptyState,
} from '../components/ui';
import JdListInput, { newJd, validateJds } from '../components/analysis/JdListInput';
import PageHeader from '../components/layout/PageHeader';
import { analyzeResume, downloadAnalysisReport } from '../services/api';

export default function Analyze() {
  const [resumeFile, setResumeFile] = useState(null);
  const [jds, setJds] = useState([newJd()]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null); // {current, total} during multi-JD run
  const [result, setResult] = useState(null);

  const onDrop = (e) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  };
  const handleFile = (f) => {
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx'].includes(ext)) {
      toast.error('Only PDF or DOCX allowed');
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      toast.error('File must be ≤ 5MB');
      return;
    }
    setResumeFile(f);
  };

  const submit = async () => {
    if (!resumeFile) return toast.error('Upload a resume first');
    const validationError = validateJds(jds);
    if (validationError) return toast.error(validationError);

    setLoading(true);
    setResult(null);
    setProgress({ current: 0, total: jds.length });

    const runs = [];
    const errors = [];

    for (let i = 0; i < jds.length; i++) {
      const jd = jds[i];
      setProgress({ current: i + 1, total: jds.length });
      try {
        const data = await analyzeResume(
          resumeFile,
          jd.mode === 'paste' ? jd.text : '',
          jd.title || `JD #${i + 1}`,
          jd.mode === 'upload' ? jd.file : null,
        );
        runs.push({
          jdId: jd.id,
          jdLabel: jd.title?.trim() || data?.jd_data?.job_title || `JD #${i + 1}`,
          data,
        });
      } catch (err) {
        const msg = err?.response?.data?.detail || 'Analysis failed';
        errors.push({
          jdLabel: jd.title?.trim() || `JD #${i + 1}`,
          error: typeof msg === 'string' ? msg : 'Analysis failed',
        });
      }
    }

    setProgress(null);
    setLoading(false);

    if (runs.length === 0) {
      toast.error(errors[0]?.error || 'Analysis failed');
      return;
    }

    // Pick the JD with the highest match score
    runs.sort((a, b) => (b.data?.match?.match_score || 0) - (a.data?.match?.match_score || 0));
    const best = runs[0];
    const others = runs.slice(1);

    setResult({
      ...best.data,
      _multiJd: {
        bestLabel: best.jdLabel,
        bestScore: best.data?.match?.match_score || 0,
        totalRun: runs.length,
        totalRequested: jds.length,
        others: others.map((r) => ({
          label: r.jdLabel,
          matchScore: r.data?.match?.match_score || 0,
          atsScore: r.data?.ats?.ats_score || 0,
          analysisId: r.data?.analysis_id,
        })),
        errors,
      },
    });

    if (jds.length > 1) {
      toast.success(`Best fit: ${best.jdLabel} (${Math.round(best.data?.match?.match_score || 0)}% match)`);
    } else {
      toast.success('Analysis complete!');
    }
  };

  const downloadPdf = async () => {
    if (!result?.analysis_id) return;
    try {
      const blob = await downloadAnalysisReport(result.analysis_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resume_report_${result.analysis_id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to download PDF');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <Loader2 className="h-10 w-10 text-brand-600 animate-spin" />
        <h3 className="mt-4 text-lg font-semibold text-slate-900">
          {progress && progress.total > 1
            ? `Analyzing JD ${progress.current} of ${progress.total}…`
            : 'Analyzing your resume…'}
        </h3>
        <p className="text-sm text-slate-500 mt-1">
          {progress && progress.total > 1
            ? "We'll pick the best match across all your job descriptions."
            : 'Parsing, scoring, and matching against the job description.'}
        </p>
      </div>
    );
  }

  if (result) {
    return (
      <AnalysisResults
        result={result}
        onReset={() => {
          setResult(null);
          setJds([newJd()]);
          setResumeFile(null);
        }}
        onDownload={downloadPdf}
      />
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="New Analysis"
        icon={FileSearch}
        title="Analyze your resume against a job"
        subtitle="Upload your resume and one or more job descriptions — we'll surface your best fit."
      />

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Resume upload */}
        <Card className="p-6">
          <CardHeader title="1. Resume" subtitle="PDF or DOCX, max 5MB" />
          <label
            htmlFor="resume-input"
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
            className="dropzone block p-8"
          >
            <input
              id="resume-input"
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />
            {resumeFile ? (
              <div className="flex items-center justify-center gap-3">
                <FileText className="h-8 w-8 text-brand-600" />
                <div className="text-left">
                  <div className="font-medium text-slate-900">{resumeFile.name}</div>
                  <div className="text-xs text-slate-500">
                    {(resumeFile.size / 1024).toFixed(1)} KB · click to change
                  </div>
                </div>
              </div>
            ) : (
              <>
                <Upload className="mx-auto h-8 w-8 text-slate-400" />
                <div className="mt-2 font-medium text-slate-900">Drop your resume here</div>
                <div className="text-sm text-slate-500">or click to browse</div>
              </>
            )}
          </label>
        </Card>

        {/* JD list input */}
        <JdListInput jds={jds} setJds={setJds} stepNumber={2} />
      </div>

      <div className="flex justify-end">
        <button
          onClick={submit}
          className="btn-primary px-6 py-2.5"
          disabled={!resumeFile}
        >
          <Sparkles className="h-4 w-4" />
          {jds.length > 1 ? `Analyze across ${jds.length} JDs` : 'Run Analysis'}
        </button>
      </div>
    </div>
  );
}

const VERDICT_THEMES = {
  excellent: {
    gradient: 'from-emerald-500 via-green-500 to-teal-500',
    chip: 'bg-emerald-500/20 text-emerald-50 ring-emerald-300/40',
    chipText: 'Resume Ready',
    Icon: PartyPopper,
  },
  good: {
    gradient: 'from-sky-500 via-indigo-500 to-blue-600',
    chip: 'bg-sky-500/20 text-sky-50 ring-sky-300/40',
    chipText: 'Almost There',
    Icon: ThumbsUp,
  },
  needs_work: {
    gradient: 'from-amber-500 via-orange-500 to-rose-500',
    chip: 'bg-amber-500/20 text-amber-50 ring-amber-200/40',
    chipText: 'Needs Work',
    Icon: AlertTriangle,
  },
  poor: {
    gradient: 'from-rose-600 via-red-600 to-slate-800',
    chip: 'bg-rose-500/20 text-rose-50 ring-rose-300/40',
    chipText: 'Work Harder',
    Icon: AlertTriangle,
  },
};

function VerdictBanner({ verdict }) {
  if (!verdict || !verdict.status) return null;
  const theme = VERDICT_THEMES[verdict.status] || VERDICT_THEMES.needs_work;
  const { Icon } = theme;
  const role = verdict.recommended_role;
  const isReady = verdict.is_ready;

  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${theme.gradient} p-7 md:p-9 text-white shadow-xl`}
    >
      <div className="absolute -top-16 -right-16 h-56 w-56 rounded-full bg-white/15 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-16 -left-16 h-56 w-56 rounded-full bg-black/10 blur-3xl pointer-events-none" />

      <div className="relative">
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 ${theme.chip} backdrop-blur`}
          >
            <Icon className="h-3.5 w-3.5" />
            {theme.chipText}
          </span>
          {role && isReady && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 backdrop-blur px-3 py-1 text-xs font-semibold ring-1 ring-white/20">
              <Target className="h-3.5 w-3.5" />
              Best fit: {role.role}
            </span>
          )}
        </div>

        <h2 className="mt-4 text-3xl md:text-4xl font-bold leading-tight">
          {verdict.headline}
        </h2>
        <p className="mt-3 text-base md:text-lg text-white/95 leading-relaxed max-w-3xl">
          {verdict.message}
        </p>

        {/* Recommended role spotlight */}
        {role && (
          <div className="mt-5 inline-flex items-center gap-3 rounded-xl bg-white/15 backdrop-blur px-4 py-3 ring-1 ring-white/20">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/25">
              <Briefcase className="h-5 w-5" />
            </span>
            <div>
              <div className="text-xs uppercase tracking-wide text-white/80">
                {isReady ? 'We recommend you apply for' : 'Aspirational role to work toward'}
              </div>
              <div className="text-lg font-bold">
                {role.role}
                <span className="ml-2 text-sm font-medium text-white/85">
                  ({Math.round(role.score)}% fit)
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Alternative roles */}
        {verdict.alternative_roles?.length > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2 text-sm text-white/90">
            <span className="font-medium">Other good fits:</span>
            {verdict.alternative_roles.map((r) => (
              <span
                key={r.role}
                className="inline-flex items-center gap-1 rounded-full bg-white/10 ring-1 ring-white/20 px-2.5 py-1 text-xs font-medium"
              >
                {r.role}
                <span className="text-white/70">{Math.round(r.score)}%</span>
              </span>
            ))}
          </div>
        )}

        {/* Next steps */}
        {verdict.next_steps?.length > 0 && (
          <div className="mt-6 rounded-xl bg-white/10 backdrop-blur ring-1 ring-white/15 p-5">
            <div className="text-sm font-semibold uppercase tracking-wide text-white/90">
              {isReady ? 'Final polish' : 'Your action plan'}
            </div>
            <ul className="mt-3 space-y-2">
              {verdict.next_steps.map((step, i) => (
                <li key={i} className="flex gap-2.5 text-sm md:text-[0.95rem] text-white/95">
                  <ArrowRight className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  <span>{step}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function AnalysisResults({ result, onReset, onDownload }) {
  const { match, ats, predicted_roles = [], recommendations = [], verdict, resume_data = {}, jd_data = {} } = result;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analysis Results</h1>
          <p className="text-slate-500 mt-1">
            {resume_data.name || 'Candidate'} · {jd_data.job_title || 'Target role'}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={onReset} className="btn-secondary">New analysis</button>
          <button onClick={onDownload} className="btn-primary">
            <Download className="h-4 w-4" /> Download PDF
          </button>
        </div>
      </div>

      {/* Multi-JD best-fit banner */}
      <MultiJdBanner multi={result._multiJd} />

      {/* Verdict banner */}
      <VerdictBanner verdict={verdict} />

      {/* Score cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <ScoreCard title="Match Score" score={match.match_score} icon={TrendingUp} description={`${match.matched_count} of ${match.total_jd_skills} JD skills matched`} />
        <ScoreCard title="ATS Score" score={ats.ats_score} icon={FileText} description={ats.score_label} />
        <ScoreCard title="Top Role Fit" score={predicted_roles[0]?.score || 0} icon={Briefcase} description={predicted_roles[0]?.role || 'No role predicted'} />
      </div>

      {/* ATS breakdown */}
      <Card className="p-6">
        <CardHeader title="ATS Breakdown" subtitle="How each component contributes to your ATS score" />
        <div className="space-y-4">
          {[
            { label: 'Keyword match', value: ats.breakdown.keyword_score, weight: '45%' },
            { label: 'Skill match', value: ats.breakdown.skill_score, weight: '25%' },
            { label: 'Section completeness', value: ats.breakdown.section_score, weight: '15%' },
            { label: 'Experience', value: ats.breakdown.experience_score, weight: '15%' },
          ].map((row) => (
            <div key={row.label}>
              <div className="flex items-center justify-between text-sm mb-1.5">
                <div className="font-medium text-slate-700">
                  {row.label} <span className="text-slate-400 font-normal">({row.weight})</span>
                </div>
                <div className="text-slate-600 tabular-nums">{Math.round(row.value)}%</div>
              </div>
              <ProgressBar value={row.value} color={row.value >= 65 ? 'green' : row.value >= 40 ? 'amber' : 'red'} />
            </div>
          ))}
        </div>
      </Card>

      {/* Skills */}
      <div className="grid lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <CardHeader title="Matched skills" subtitle={`${match.matched_skills.length} skills found`} />
          {match.matched_skills.length === 0 ? (
            <EmptyState icon={CheckCircle2} title="No skills matched yet" description="Try a more relevant job description." />
          ) : (
            <div className="flex flex-wrap gap-2">
              {match.matched_skills.map((s) => (
                <span key={s} className="badge-green"><CheckCircle2 className="h-3 w-3" /> {s}</span>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-6">
          <CardHeader title="Missing skills" subtitle={`${match.missing_skills.length} gaps to close`} />
          {match.missing_skills.length === 0 ? (
            <div className="flex items-center gap-2 text-emerald-600 text-sm font-medium">
              <CheckCircle2 className="h-5 w-5" /> Great — your resume covers every required skill!
            </div>
          ) : (
            <div className="flex flex-wrap gap-2">
              {match.missing_skills.map((s) => (
                <span key={s} className="badge-red"><XCircle className="h-3 w-3" /> {s}</span>
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Roles */}
      {predicted_roles.length > 0 && (
        <Card className="p-6">
          <CardHeader title="Predicted roles" subtitle="Top role fits based on your resume skills" />
          <div className="space-y-3">
            {predicted_roles.map((r) => (
              <div key={r.role} className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4">
                <div className="sm:w-48 flex-shrink-0 text-sm font-medium text-slate-800">{r.role}</div>
                <div className="flex-1 flex items-center gap-3">
                  <div className="flex-1"><ProgressBar value={r.score} color="brand" /></div>
                  <div className="w-12 text-sm font-semibold text-slate-700 text-right flex-shrink-0">{Math.round(r.score)}%</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card className="p-6">
          <CardHeader title="Personalized recommendations" subtitle="Concrete steps to improve your fit" />
          <ul className="space-y-3">
            {recommendations.map((r, i) => (
              <li key={i} className="flex gap-3">
                <span className="flex-shrink-0 mt-0.5 flex h-6 w-6 items-center justify-center rounded-full bg-brand-100 text-brand-700 text-xs font-semibold">
                  {i + 1}
                </span>
                <span className="text-sm text-slate-700">{r}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function MultiJdBanner({ multi }) {
  if (!multi || multi.totalRequested <= 1) return null;
  return (
    <Card className="p-5 bg-gradient-to-r from-brand-50 to-indigo-50 ring-1 ring-brand-200/60">
      <div className="flex flex-wrap items-start gap-4 justify-between">
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-brand-600 text-white flex-shrink-0">
            <Trophy className="h-5 w-5" />
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              Best fit out of {multi.totalRun} JDs
            </div>
            <div className="text-lg font-bold text-slate-900 mt-0.5">{multi.bestLabel}</div>
            <div className="text-sm text-slate-600 mt-0.5">
              {Math.round(multi.bestScore)}% match score — showing this analysis below.
            </div>
          </div>
        </div>
      </div>

      {multi.others.length > 0 && (
        <div className="mt-4 pt-4 border-t border-brand-200/60">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Other JDs analyzed
          </div>
          <div className="space-y-1.5">
            {multi.others.map((o, i) => (
              <div key={i} className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-700 truncate">{o.label}</span>
                <span className="inline-flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs text-slate-500">Match</span>
                  <span className="font-semibold tabular-nums text-slate-700">
                    {Math.round(o.matchScore)}%
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {multi.errors?.length > 0 && (
        <div className="mt-3 text-xs text-amber-700">
          <AlertTriangle className="inline h-3.5 w-3.5 mr-1" />
          {multi.errors.length} JD{multi.errors.length > 1 ? 's' : ''} failed to analyze
        </div>
      )}
    </Card>
  );
}
