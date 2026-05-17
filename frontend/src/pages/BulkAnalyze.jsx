import React, { useRef, useState } from 'react';
import {
  Upload,
  FileText,
  Trash2,
  Sparkles,
  Loader2,
  Trophy,
  Medal,
  Award,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle,
  Mail,
  Plus,
  AlertTriangle,
  Briefcase,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { Card, CardHeader } from '../components/ui';
import JdListInput, { newJd, validateJds } from '../components/analysis/JdListInput';
import PageHeader from '../components/layout/PageHeader';
import { Users as UsersIcon } from 'lucide-react';
import { analyzeBulk } from '../services/api';

const VERDICT_BADGE = {
  excellent: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
  good: 'bg-sky-100 text-sky-800 ring-sky-200',
  needs_work: 'bg-amber-100 text-amber-800 ring-amber-200',
  poor: 'bg-rose-100 text-rose-800 ring-rose-200',
};

const VERDICT_LABEL = {
  excellent: 'Ready',
  good: 'Almost there',
  needs_work: 'Needs work',
  poor: 'Not ready',
};

export default function BulkAnalyze() {
  const [resumes, setResumes] = useState([]); // [{file, id}]
  const [jds, setJds] = useState([newJd()]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const inputRef = useRef(null);

  const addFiles = (files) => {
    const next = [];
    for (const f of files) {
      const ext = f.name.split('.').pop().toLowerCase();
      if (!['pdf', 'docx'].includes(ext)) {
        toast.error(`${f.name}: only PDF/DOCX`);
        continue;
      }
      if (f.size > 5 * 1024 * 1024) {
        toast.error(`${f.name}: must be ≤ 5MB`);
        continue;
      }
      next.push({ file: f, id: `${f.name}-${f.size}-${Math.random().toString(36).slice(2, 7)}` });
    }
    if (resumes.length + next.length > 20) {
      toast.error('Maximum 20 resumes per comparison');
      return;
    }
    setResumes((prev) => [...prev, ...next]);
  };

  const removeResume = (id) => {
    setResumes((prev) => prev.filter((r) => r.id !== id));
  };

  const onResumeDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files?.length) addFiles(Array.from(e.dataTransfer.files));
  };

  const submit = async () => {
    if (resumes.length < 2) return toast.error('Add at least 2 resumes to compare');
    const validationError = validateJds(jds);
    if (validationError) return toast.error(validationError);

    setLoading(true);
    setResult(null);
    setExpanded(null);
    setProgress({ current: 0, total: jds.length });
    const t = toast.loading(
      jds.length > 1
        ? `Analyzing ${resumes.length} resumes against ${jds.length} JDs…`
        : `Analyzing ${resumes.length} resumes…`,
    );

    const runs = []; // {jdLabel, data}
    const runErrors = [];

    for (let i = 0; i < jds.length; i++) {
      const jd = jds[i];
      setProgress({ current: i + 1, total: jds.length });
      try {
        const data = await analyzeBulk(
          resumes.map((r) => r.file),
          jd.mode === 'paste' ? jd.text : '',
          jd.title || `JD #${i + 1}`,
          jd.mode === 'upload' ? jd.file : null,
        );
        runs.push({
          jdLabel: jd.title?.trim() || data?.job_title || `JD #${i + 1}`,
          data,
        });
      } catch (err) {
        const detail = err?.response?.data?.detail;
        const msg = typeof detail === 'string' ? detail : detail?.message || 'Bulk analysis failed';
        runErrors.push({ jdLabel: jd.title?.trim() || `JD #${i + 1}`, error: msg });
      }
    }

    setProgress(null);
    setLoading(false);

    if (runs.length === 0) {
      toast.error(runErrors[0]?.error || 'Bulk analysis failed', { id: t });
      return;
    }

    if (runs.length === 1 && jds.length === 1) {
      // Single-JD path — keep original payload shape
      setResult({
        ...runs[0].data,
        _multiJd: null,
        _runErrors: runErrors,
      });
      toast.success(`Ranked ${runs[0].data.candidates.length} candidates`, { id: t });
      return;
    }

    // Multi-JD aggregation: pick the best JD per candidate (by composite_score),
    // then re-rank candidates by their winning composite.
    const bestByFile = new Map(); // file_name -> {candidate, jdLabel}
    const aggregatedErrors = [];

    for (const run of runs) {
      for (const c of run.data.candidates || []) {
        const key = c.file_name;
        const existing = bestByFile.get(key);
        if (!existing || c.composite_score > existing.candidate.composite_score) {
          bestByFile.set(key, { candidate: { ...c, best_jd_label: run.jdLabel }, jdLabel: run.jdLabel });
        }
      }
      for (const e of run.data.errors || []) {
        aggregatedErrors.push({ ...e, jd_label: run.jdLabel });
      }
    }

    const merged = Array.from(bestByFile.values())
      .map((entry) => entry.candidate)
      .sort((a, b) => b.composite_score - a.composite_score)
      .map((c, i) => ({ ...c, rank: i + 1 }));

    setResult({
      candidates: merged,
      errors: aggregatedErrors,
      job_title: runs.map((r) => r.jdLabel).join(' · '),
      _multiJd: {
        jdLabels: runs.map((r) => r.jdLabel),
        totalRun: runs.length,
        totalRequested: jds.length,
      },
      _runErrors: runErrors,
    });

    toast.success(
      `Ranked ${merged.length} candidate${merged.length === 1 ? '' : 's'} across ${runs.length} JDs`,
      { id: t },
    );
  };

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Compare Resumes"
        icon={UsersIcon}
        title="Rank candidates side-by-side"
        subtitle="Upload multiple resumes, compare against one or more job descriptions, and see them ranked best to worst."
      />

      {!result && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Resumes */}
          <Card className="p-6">
            <CardHeader title="1. Resumes" subtitle="Add 2-20 resumes (PDF or DOCX, max 5MB each)" />
            <input
              ref={inputRef}
              type="file"
              accept=".pdf,.docx"
              multiple
              className="hidden"
              onChange={(e) => e.target.files?.length && addFiles(Array.from(e.target.files))}
            />

            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={onResumeDrop}
              onClick={() => inputRef.current?.click()}
              className="border-2 border-dashed border-slate-300 rounded-xl p-6 text-center cursor-pointer hover:border-brand-400 hover:bg-brand-50/40 transition"
            >
              <Upload className="mx-auto h-7 w-7 text-slate-400" />
              <div className="mt-2 font-medium text-slate-900">Drop resumes here</div>
              <div className="text-sm text-slate-500">or click to browse · multiple selection</div>
            </div>

            {resumes.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span>{resumes.length} resume{resumes.length === 1 ? '' : 's'} ready</span>
                  <button
                    onClick={() => setResumes([])}
                    className="text-rose-600 hover:underline"
                  >
                    Clear all
                  </button>
                </div>
                <ul className="divide-y divide-slate-100 rounded-lg ring-1 ring-slate-200 bg-white">
                  {resumes.map((r) => (
                    <li key={r.id} className="flex items-center gap-3 px-3 py-2.5">
                      <FileText className="h-4 w-4 text-brand-600 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-slate-900 truncate">{r.file.name}</div>
                        <div className="text-xs text-slate-500">
                          {(r.file.size / 1024).toFixed(1)} KB
                        </div>
                      </div>
                      <button
                        onClick={() => removeResume(r.id)}
                        className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                        title="Remove"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </li>
                  ))}
                </ul>
                <button
                  onClick={() => inputRef.current?.click()}
                  className="text-sm text-brand-600 hover:text-brand-700 inline-flex items-center gap-1.5 mt-2"
                >
                  <Plus className="h-3.5 w-3.5" /> Add more
                </button>
              </div>
            )}
          </Card>

          {/* JD list */}
          <JdListInput jds={jds} setJds={setJds} stepNumber={2} />
        </div>
      )}

      {!result && (
        <div className="flex justify-end">
          <button
            onClick={submit}
            disabled={loading || resumes.length < 2}
            className="btn-primary px-6 py-2.5 disabled:opacity-60"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {progress && progress.total > 1
                  ? ` Analyzing JD ${progress.current}/${progress.total}…`
                  : ' Analyzing…'}
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                {jds.length > 1 ? ` Rank Resumes across ${jds.length} JDs` : ' Rank Resumes'}
              </>
            )}
          </button>
        </div>
      )}

      {result && (
        <RankedResults
          result={result}
          expanded={expanded}
          setExpanded={setExpanded}
          onReset={() => {
            setResult(null);
            setExpanded(null);
          }}
        />
      )}
    </div>
  );
}

/* ---------- Ranked results table ---------- */

function rankIcon(rank) {
  if (rank === 1) return <Trophy className="h-5 w-5 text-yellow-500" />;
  if (rank === 2) return <Medal className="h-5 w-5 text-slate-400" />;
  if (rank === 3) return <Award className="h-5 w-5 text-amber-700" />;
  return <span className="text-sm font-bold text-slate-500">#{rank}</span>;
}

function scoreTone(s) {
  if (s >= 75) return 'text-emerald-700 bg-emerald-50 ring-emerald-200';
  if (s >= 60) return 'text-sky-700 bg-sky-50 ring-sky-200';
  if (s >= 40) return 'text-amber-700 bg-amber-50 ring-amber-200';
  return 'text-rose-700 bg-rose-50 ring-rose-200';
}

function RankedResults({ result, expanded, setExpanded, onReset }) {
  const { candidates = [], errors = [], job_title, _multiJd: multi } = result;
  const winner = candidates[0];
  const isMultiJd = !!multi && multi.totalRun > 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Ranking Results</h2>
          <p className="text-sm text-slate-500">
            {candidates.length} candidates ranked
            {isMultiJd ? (
              <>
                {' '}across{' '}
                <span className="font-medium text-slate-700">{multi.totalRun} JDs</span>
                {' '}— each candidate matched against their best fit
              </>
            ) : (
              <>
                {' '}for{' '}
                <span className="font-medium text-slate-700">{job_title}</span>
              </>
            )}
          </p>
        </div>
        <button onClick={onReset} className="btn-secondary">
          New comparison
        </button>
      </div>

      {isMultiJd && (
        <Card className="p-4 bg-gradient-to-r from-brand-50 to-indigo-50 ring-1 ring-brand-200/60">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-white flex-shrink-0">
              <Briefcase className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="text-xs font-semibold uppercase tracking-wide text-brand-700">
                Compared across {multi.totalRun} job description{multi.totalRun === 1 ? '' : 's'}
              </div>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {multi.jdLabels.map((label) => (
                  <span
                    key={label}
                    className="inline-flex items-center px-2 py-0.5 rounded-md bg-white ring-1 ring-brand-200/70 text-xs font-medium text-slate-700"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Winner spotlight */}
      {winner && (
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-yellow-400 via-amber-500 to-orange-500 p-5 sm:p-7 text-white shadow-xl">
          <div className="absolute -top-16 -right-16 h-56 w-56 rounded-full bg-white/15 blur-3xl pointer-events-none" />
          <div className="relative flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center gap-5 justify-between">
            <div className="min-w-0">
              <div className="inline-flex items-center gap-2 rounded-full bg-white/20 backdrop-blur px-3 py-1 text-xs font-semibold ring-1 ring-white/30">
                <Trophy className="h-3.5 w-3.5" /> Top candidate
              </div>
              <h3 className="mt-3 text-2xl sm:text-3xl font-bold break-words">{winner.candidate_name}</h3>
              <div className="text-white/90 text-sm mt-1 truncate">{winner.file_name}</div>
            </div>
            <div className="grid grid-cols-3 gap-3 sm:gap-4 text-center w-full sm:w-auto">
              <ScoreChip label="Composite" value={winner.composite_score} />
              <ScoreChip label="ATS" value={winner.ats_score} />
              <ScoreChip label="JD Match" value={winner.match_score} />
            </div>
          </div>
        </div>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <Card className="p-4 border border-amber-200 bg-amber-50">
          <div className="flex gap-2 items-start">
            <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800">
              <div className="font-semibold">{errors.length} file(s) couldn't be analyzed</div>
              <ul className="mt-1 list-disc pl-5">
                {errors.map((e, i) => (
                  <li key={i}>
                    <span className="font-medium">{e.file_name}:</span> {e.error}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Card>
      )}

      {/* Ranked table */}
      <Card className="p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-4 py-3 w-14">Rank</th>
                <th className="px-4 py-3">Candidate</th>
                {isMultiJd && <th className="px-4 py-3">Best JD</th>}
                <th className="px-4 py-3">ATS</th>
                <th className="px-4 py-3">JD Match</th>
                <th className="px-4 py-3">Role Fit</th>
                <th className="px-4 py-3">Composite</th>
                <th className="px-4 py-3">Verdict</th>
                <th className="px-4 py-3 w-10"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {candidates.map((c) => {
                const isOpen = expanded === c.candidate_id;
                return (
                  <React.Fragment key={c.candidate_id}>
                    <tr
                      className="hover:bg-slate-50/60 cursor-pointer"
                      onClick={() => setExpanded(isOpen ? null : c.candidate_id)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-center h-7 w-7">{rankIcon(c.rank)}</div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-900">{c.candidate_name}</div>
                        <div className="text-xs text-slate-500 flex items-center gap-1.5">
                          <FileText className="h-3 w-3" />
                          <span className="truncate max-w-[200px]">{c.file_name}</span>
                          {c.email && (
                            <>
                              <span>·</span>
                              <Mail className="h-3 w-3" />
                              <span className="truncate max-w-[160px]">{c.email}</span>
                            </>
                          )}
                        </div>
                      </td>
                      {isMultiJd && (
                        <td className="px-4 py-3">
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-brand-50 text-brand-700 ring-1 ring-brand-200 text-xs font-medium">
                            <Briefcase className="h-3 w-3" />
                            <span className="truncate max-w-[140px]">{c.best_jd_label}</span>
                          </span>
                        </td>
                      )}
                      <td className="px-4 py-3">
                        <ScoreCell value={c.ats_score} />
                      </td>
                      <td className="px-4 py-3">
                        <ScoreCell value={c.match_score} />
                      </td>
                      <td className="px-4 py-3">
                        <ScoreCell value={c.role_fit_score} />
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2.5 py-1 rounded-md ring-1 font-bold tabular-nums ${scoreTone(
                            c.composite_score,
                          )}`}
                        >
                          {Math.round(c.composite_score)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ring-1 ${
                            VERDICT_BADGE[c.verdict?.status] || VERDICT_BADGE.needs_work
                          }`}
                        >
                          {VERDICT_LABEL[c.verdict?.status] || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">
                        {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-slate-50/40">
                        <td colSpan={isMultiJd ? 9 : 8} className="px-4 py-4">
                          <CandidateDetails c={c} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function ScoreCell({ value }) {
  const v = Math.round(value || 0);
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded ring-1 text-xs font-semibold tabular-nums ${scoreTone(v)}`}>
      {v}%
    </span>
  );
}

function ScoreChip({ label, value }) {
  return (
    <div className="bg-white/15 backdrop-blur rounded-lg px-3 py-2 ring-1 ring-white/25">
      <div className="text-3xl font-bold tabular-nums">{Math.round(value || 0)}</div>
      <div className="text-xs uppercase tracking-wide text-white/80 mt-0.5">{label}</div>
    </div>
  );
}

function CandidateDetails({ c }) {
  return (
    <div className="grid md:grid-cols-2 gap-5">
      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
          Matched skills ({c.matched_count}/{c.total_jd_skills})
        </div>
        {c.matched_skills?.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {c.matched_skills.map((s) => (
              <span
                key={s}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 text-xs font-medium"
              >
                <CheckCircle2 className="h-3 w-3" /> {s}
              </span>
            ))}
          </div>
        ) : (
          <div className="text-xs text-slate-400">None</div>
        )}
      </div>

      <div>
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
          Missing skills
        </div>
        {c.missing_skills?.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {c.missing_skills.slice(0, 20).map((s) => (
              <span
                key={s}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-rose-50 text-rose-700 ring-1 ring-rose-200 text-xs font-medium"
              >
                <XCircle className="h-3 w-3" /> {s}
              </span>
            ))}
            {c.missing_skills.length > 20 && (
              <span className="text-xs text-slate-400">+{c.missing_skills.length - 20} more</span>
            )}
          </div>
        ) : (
          <div className="text-xs text-slate-400">None — full coverage</div>
        )}
      </div>

      {c.verdict?.message && (
        <div className="md:col-span-2 rounded-lg bg-white ring-1 ring-slate-200 p-4">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Verdict</div>
          <div className="font-semibold text-slate-900 mt-1">{c.verdict.headline}</div>
          <p className="text-sm text-slate-600 mt-1">{c.verdict.message}</p>
          {c.top_role && (
            <div className="text-xs text-slate-500 mt-2">
              Best-fit role:{' '}
              <span className="font-medium text-slate-700">{c.top_role}</span>{' '}
              ({Math.round(c.role_fit_score)}%)
            </div>
          )}
        </div>
      )}
    </div>
  );
}
