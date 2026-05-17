import React, { useEffect, useRef, useState } from 'react';
import {
  Upload,
  RefreshCw,
  FileText,
  Mail,
  Phone,
  Link2,
  ExternalLink,
  Briefcase,
  GraduationCap,
  Award,
  Folder,
  Sparkles,
  Loader2,
  CheckCircle2,
  Trash2,
  Target,
  ArrowRight,
  PartyPopper,
  ThumbsUp,
  AlertTriangle,
  ShieldCheck,
  X,
  Code2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { Card, CardHeader, EmptyState, Spinner } from '../components/ui';
import { getUserProfile, uploadProfileResume, deleteUserProfile } from '../services/api';

export default function Dashboard({ user, onNavigate }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const data = await getUserProfile();
      setProfile(data);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleUpload = async (file) => {
    if (!file) return;
    const ext = file.name.toLowerCase().split('.').pop();
    if (!['pdf', 'docx'].includes(ext)) {
      toast.error('Please upload a PDF or DOCX file');
      return;
    }
    setUploading(true);
    try {
      const data = await uploadProfileResume(file);
      setProfile(data);
      toast.success(profile ? 'Resume updated!' : 'Resume uploaded!');
    } catch (e) {
      const detail = e?.response?.data?.detail;
      const status = e?.response?.status;
      toast.error(
        typeof detail === 'string'
          ? detail
          : status
          ? `Upload failed (HTTP ${status})`
          : e?.message || 'Upload failed',
      );
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-24 text-slate-400">
        <Spinner size={8} />
      </div>
    );
  }

  if (!profile) {
    return <UploadHero user={user} uploading={uploading} onUpload={handleUpload} />;
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete your stored resume profile? This cannot be undone.')) return;
    try {
      await deleteUserProfile();
      setProfile(null);
      toast.success('Resume profile deleted');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Failed to delete');
    }
  };

  return (
    <ProfileDashboard
      profile={profile}
      user={user}
      uploading={uploading}
      onUpload={handleUpload}
      onDelete={handleDelete}
      onNavigate={onNavigate}
    />
  );
}

/* ---------- Empty state ---------- */
function UploadHero({ user, uploading, onUpload }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-900">
          Welcome, {user?.full_name?.split(' ')[0] || 'there'} 👋
        </h1>
        <p className="text-slate-500 mt-1.5">
          Upload your resume to build your AI-powered profile.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onUpload(f);
        }}
        onClick={(e) => {
          // Only open picker when the bare zone is clicked, not a child button/input.
          if (e.target === e.currentTarget) inputRef.current?.click();
        }}
        className={`relative cursor-pointer rounded-2xl border-2 border-dashed p-16 text-center transition ${
          drag
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-slate-300 bg-white hover:border-indigo-400 hover:bg-indigo-50/40'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            // Reset so picking the same file again re-triggers onChange
            e.target.value = '';
            if (f) onUpload(f);
          }}
        />
        <div className="mx-auto h-16 w-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white flex items-center justify-center shadow-lg shadow-indigo-500/30">
          {uploading ? <Loader2 className="h-7 w-7 animate-spin" /> : <Upload className="h-7 w-7" />}
        </div>
        <h2 className="mt-5 text-xl font-semibold text-slate-900">
          {uploading ? 'Analyzing your resume…' : 'Upload your resume'}
        </h2>
        <p className="mt-2 text-slate-500">
          Drop a PDF or DOCX here, or click to browse. We&apos;ll extract everything automatically.
        </p>
        {!uploading && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              inputRef.current?.click();
            }}
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-2.5 text-sm font-semibold shadow-md hover:from-indigo-700 hover:to-purple-700"
          >
            <Upload className="h-4 w-4" /> Choose File
          </button>
        )}
      </div>
    </div>
  );
}

/* ---------- Filled dashboard ---------- */
function ProfileDashboard({ profile, user, uploading, onUpload, onDelete, onNavigate }) {
  const inputRef = useRef(null);
  const resume = profile.resume || {};
  const summary = profile.experience_summary || { certifications: 0, education: 0, projects: 0 };
  const grouped = profile.skills_grouped || { programming: [], frameworks_tools: [], other: [] };
  const roles = profile.predicted_roles || [];
  const displayName = resume.name || profile.user_name || user?.full_name || 'Your Profile';

  return (
    <div className="space-y-6">
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = '';
          if (f) onUpload(f);
        }}
      />

      {/* Header */}
      <div className="rounded-2xl bg-gradient-to-r from-indigo-600 to-purple-600 p-7 text-white shadow-xl relative overflow-hidden">
        <div className="absolute -top-10 -right-10 w-64 h-64 bg-white/10 rounded-full blur-3xl" />
        <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-5">
          <div>
            <div className="flex items-center gap-2 text-indigo-100 text-sm">
              <Sparkles className="h-4 w-4" /> AI-Powered Profile
            </div>
            <h1 className="mt-1 text-3xl font-bold">{displayName}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-indigo-100">
              {(resume.email || user?.email) && (
                <span className="inline-flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5" /> {resume.email || user?.email}
                </span>
              )}
              {resume.phone && (
                <span className="inline-flex items-center gap-1.5">
                  <Phone className="h-3.5 w-3.5" /> {resume.phone}
                </span>
              )}
              {resume.linkedin && (
                <span className="inline-flex items-center gap-1.5">
                  <Link2 className="h-3.5 w-3.5" /> {resume.linkedin}
                </span>
              )}
              {resume.github && (
                <span className="inline-flex items-center gap-1.5">
                  <ExternalLink className="h-3.5 w-3.5" /> {resume.github}
                </span>
              )}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => inputRef.current?.click()}
              disabled={uploading}
              className="inline-flex items-center gap-2 rounded-lg bg-white text-indigo-700 px-4 py-2 text-sm font-semibold hover:bg-indigo-50 disabled:opacity-60"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              {uploading ? 'Updating…' : 'Update Resume'}
            </button>
            <button
              onClick={onDelete}
              disabled={uploading}
              title="Delete resume profile"
              aria-label="Delete resume profile"
              className="inline-flex items-center justify-center rounded-lg bg-white/10 text-white ring-1 ring-white/30 h-10 w-10 hover:bg-red-500 hover:ring-red-400 transition disabled:opacity-50"
            >
              <Trash2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => onNavigate && onNavigate('analyze')}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-700/40 text-white ring-1 ring-white/30 px-4 py-2 text-sm font-semibold hover:bg-indigo-700/60"
            >
              <FileText className="h-4 w-4" /> Run JD Analysis
            </button>
          </div>
        </div>
      </div>

      {/* Top row: experience summary pie + stats */}
      <div className="grid lg:grid-cols-3 gap-6">
        <Card className="p-6 lg:col-span-1">
          <CardHeader title="Experience Summary" subtitle="Overview of experiences" />
          <ExperiencePie summary={summary} />
        </Card>

        <Card className="p-6 lg:col-span-2">
          <CardHeader
            title="Career Progress"
            subtitle="AI-generated insights based on your projects and experiences"
            right={<Sparkles className="h-4 w-4 text-indigo-500" />}
          />
          {roles.length === 0 ? (
            <EmptyState
              title="No role predictions yet"
              description="Add more skills to your resume for accurate role matching."
            />
          ) : (
            <div className="space-y-4 mt-2">
              {roles.map((r) => (
                <RoleBar key={r.role} role={r} />
              ))}
            </div>
          )}
        </Card>
      </div>

      {/* Skills */}
      <Card className="p-6">
        <CardHeader
          title="Skills"
          subtitle={`${(resume.skills || []).length} skills extracted from your resume`}
        />
        <SkillsBlocks grouped={grouped} />
      </Card>

      {/* Other resume sections */}
      <div className="grid md:grid-cols-2 gap-6">
        <ProjectsCard projects={resume.projects} />
        <ListCard
          title="Certifications"
          icon={<Award className="h-4 w-4 text-amber-500" />}
          items={resume.certifications}
          emptyText="No certifications detected"
        />
        <ListCard
          title="Work Experience"
          icon={<Briefcase className="h-4 w-4 text-purple-500" />}
          items={resume.work_experience}
          emptyText="No work experience listed"
        />
        <Card className="p-6">
          <CardHeader title="Education" icon={<GraduationCap className="h-4 w-4 text-pink-500" />} />
          {(() => {
            const entries = educationEntries(resume.education);
            if (entries.length === 0) {
              return <p className="text-sm text-slate-400 mt-1">No education information found</p>;
            }
            return (
              <ul className="mt-2 space-y-2">
                {entries.map((entry, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-pink-400 flex-shrink-0" />
                    <span>{entry}</span>
                  </li>
                ))}
              </ul>
            );
          })()}
          {typeof resume.experience !== 'undefined' && resume.experience !== null && (
            <p className="text-sm text-slate-500 mt-3 pt-3 border-t border-slate-100">
              <span className="font-medium text-slate-700">Years of experience:</span>{' '}
              {String(resume.experience)}
            </p>
          )}
        </Card>
      </div>

      {/* Resume Verdict + ATS assessment (below dashboard sections) */}
      <ProfileVerdict assessment={profile.assessment} />
    </div>
  );
}

/* ---------- Verdict + ATS card (below dashboard) ---------- */

const VERDICT_THEMES = {
  excellent: {
    gradient: 'from-emerald-500 via-green-500 to-teal-500',
    chipBg: 'bg-emerald-500/20 ring-emerald-300/40',
    chipText: 'Resume Ready',
    Icon: PartyPopper,
    ringColor: 'stroke-emerald-300',
  },
  good: {
    gradient: 'from-sky-500 via-indigo-500 to-blue-600',
    chipBg: 'bg-sky-500/20 ring-sky-300/40',
    chipText: 'Almost There',
    Icon: ThumbsUp,
    ringColor: 'stroke-sky-300',
  },
  needs_work: {
    gradient: 'from-amber-500 via-orange-500 to-rose-500',
    chipBg: 'bg-amber-500/20 ring-amber-200/40',
    chipText: 'Needs Work',
    Icon: AlertTriangle,
    ringColor: 'stroke-amber-200',
  },
  poor: {
    gradient: 'from-rose-600 via-red-600 to-slate-800',
    chipBg: 'bg-rose-500/20 ring-rose-300/40',
    chipText: 'Work Harder',
    Icon: AlertTriangle,
    ringColor: 'stroke-rose-300',
  },
};

const BREAKDOWN_LABELS = {
  section_completeness: 'Section completeness',
  skill_breadth: 'Skill breadth',
  experience_signal: 'Experience signal',
  education_signal: 'Education signal',
  contact_completeness: 'Contact info',
  structure_quality: 'Structure & wording',
};

function ProfileVerdict({ assessment }) {
  if (!assessment || !assessment.verdict || !assessment.ats) return null;
  const { verdict, ats } = assessment;
  const theme = VERDICT_THEMES[verdict.status] || VERDICT_THEMES.needs_work;
  const { Icon } = theme;
  const role = verdict.recommended_role;
  const score = Math.round(ats.ats_score || 0);

  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${theme.gradient} p-7 md:p-9 text-white shadow-xl`}
    >
      <div className="absolute -top-20 -right-20 h-72 w-72 rounded-full bg-white/15 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-16 -left-16 h-56 w-56 rounded-full bg-black/10 blur-3xl pointer-events-none" />

      <div className="relative grid lg:grid-cols-3 gap-8 items-start">
        {/* Left: Verdict text */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ring-1 backdrop-blur ${theme.chipBg}`}
            >
              <Icon className="h-3.5 w-3.5" />
              {theme.chipText}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 backdrop-blur px-3 py-1 text-xs font-semibold ring-1 ring-white/20">
              <ShieldCheck className="h-3.5 w-3.5" />
              ATS-only score (no JD)
            </span>
            {role && verdict.is_ready && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 backdrop-blur px-3 py-1 text-xs font-semibold ring-1 ring-white/20">
                <Target className="h-3.5 w-3.5" />
                Best fit: {role.role}
              </span>
            )}
          </div>

          <h2 className="text-3xl md:text-4xl font-bold leading-tight">
            {verdict.headline}
          </h2>
          <p className="text-base md:text-lg text-white/95 leading-relaxed max-w-2xl">
            {verdict.message}
          </p>

          {role && (
            <div className="inline-flex items-center gap-3 rounded-xl bg-white/15 backdrop-blur px-4 py-3 ring-1 ring-white/20">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-white/25">
                <Briefcase className="h-5 w-5" />
              </span>
              <div>
                <div className="text-xs uppercase tracking-wide text-white/80">
                  {verdict.is_ready ? 'We recommend you apply for' : 'Aspirational role to work toward'}
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

          {verdict.alternative_roles?.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 text-sm text-white/90">
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
        </div>

        {/* Right: ATS dial */}
        <div className="flex flex-col items-center justify-center rounded-2xl bg-white/10 backdrop-blur ring-1 ring-white/20 p-6">
          <AtsDial score={score} ringColor={theme.ringColor} />
          <div className="mt-3 text-center">
            <div className="text-xs uppercase tracking-wide text-white/80">Resume ATS Score</div>
            <div className="text-base font-semibold mt-0.5">{ats.label}</div>
          </div>
        </div>
      </div>

      {/* ATS breakdown + next steps */}
      <div className="relative mt-7 grid lg:grid-cols-2 gap-5">
        <div className="rounded-xl bg-white/10 backdrop-blur ring-1 ring-white/15 p-5">
          <div className="text-sm font-semibold uppercase tracking-wide text-white/90">
            ATS breakdown
          </div>
          <div className="mt-3 space-y-2.5">
            {Object.entries(ats.breakdown || {}).map(([key, val]) => (
              <BreakdownBar key={key} label={BREAKDOWN_LABELS[key] || key} value={val} />
            ))}
          </div>
        </div>

        {verdict.next_steps?.length > 0 && (
          <div className="rounded-xl bg-white/10 backdrop-blur ring-1 ring-white/15 p-5">
            <div className="text-sm font-semibold uppercase tracking-wide text-white/90">
              {verdict.is_ready ? 'Final polish' : 'Your action plan'}
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

function AtsDial({ score, ringColor }) {
  const size = 140;
  const r = 58;
  const stroke = 12;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, score));
  const dash = (pct / 100) * circ;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="block">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="rgba(255,255,255,0.18)" strokeWidth={stroke} />
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill="none"
        strokeWidth={stroke}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${circ - dash}`}
        transform={`rotate(-90 ${cx} ${cy})`}
        className={ringColor}
        style={{ stroke: 'currentColor', transition: 'stroke-dasharray 0.6s ease' }}
      />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        className="fill-white"
        style={{ fontSize: 30, fontWeight: 700 }}
      >
        {pct}
      </text>
      <text
        x="50%"
        y="68%"
        dominantBaseline="central"
        textAnchor="middle"
        className="fill-white/80"
        style={{ fontSize: 11, fontWeight: 500, letterSpacing: 1 }}
      >
        / 100
      </text>
    </svg>
  );
}

function BreakdownBar({ label, value }) {
  const v = Math.max(0, Math.min(100, Math.round(value || 0)));
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-white/90">
        <span>{label}</span>
        <span className="font-semibold tabular-nums">{v}</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-white/15 overflow-hidden">
        <div
          className="h-full bg-white/85 rounded-full"
          style={{ width: `${v}%`, transition: 'width 0.6s ease' }}
        />
      </div>
    </div>
  );
}

/* ---------- helpers ---------- */

function educationEntries(edu) {
  if (!edu) return [];
  let raw = [];
  if (typeof edu === 'string') {
    raw = edu.split(/\s*\|\s*/);
  } else if (Array.isArray(edu)) {
    raw = edu.flatMap((e) =>
      typeof e === 'string'
        ? e.split(/\s*\|\s*/)
        : [Object.values(e || {}).filter(Boolean).join(' — ')]
    );
  } else if (typeof edu === 'object') {
    raw = [Object.values(edu).filter(Boolean).join(' — ')];
  } else {
    raw = [String(edu)];
  }

  // Filter out empty entries and table-header-like rows pulled from the resume
  const headerWords = ['degree', 'program', 'university', 'board', 'institute', 'year', 'cgpa', 'percentage', 'grade'];
  return raw
    .map((s) => (s || '').trim())
    .filter(Boolean)
    .filter((s) => {
      const lower = s.toLowerCase();
      const tokens = lower.split(/[\s/]+/).filter(Boolean);
      if (tokens.length === 0) return false;
      const headerTokenCount = tokens.filter((t) => headerWords.includes(t)).length;
      // Drop if most tokens are header words AND no digits (real entries usually contain a year/grade)
      if (headerTokenCount / tokens.length >= 0.6 && !/\d/.test(s)) return false;
      return true;
    });
}

function ExperiencePie({ summary }) {
  const [hovered, setHovered] = useState(null);
  const segments = [
    { key: 'certifications', label: 'certification', color: '#6366f1', value: summary.certifications || 0 },
    { key: 'education', label: 'education', color: '#a855f7', value: summary.education || 0 },
    { key: 'projects', label: 'project', color: '#ec4899', value: summary.projects || 0 },
  ];
  const total = segments.reduce((s, seg) => s + seg.value, 0);

  if (total === 0) {
    return (
      <div className="text-center py-6 text-slate-400 text-sm">
        Not enough data to chart yet.
      </div>
    );
  }

  const size = 180;
  const r = 70;
  const stroke = 28;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  let offset = 0;

  const activeSeg = hovered ? segments.find((s) => s.key === hovered) : null;
  const centerNumber = activeSeg ? activeSeg.value : total;
  const centerLabel = activeSeg ? activeSeg.label : null;
  const centerColor = activeSeg ? activeSeg.color : '#0f172a';

  return (
    <div className="flex flex-col items-center mt-2">
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="block"
        onMouseLeave={() => setHovered(null)}
      >
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f1f5f9" strokeWidth={stroke} />
        {segments.map((seg) => {
          if (seg.value === 0) return null;
          const len = (seg.value / total) * circ;
          const dasharray = `${len} ${circ - len}`;
          const dashoffset = -offset;
          offset += len;
          const isActive = hovered === seg.key;
          const dim = hovered && !isActive;
          return (
            <circle
              key={seg.key}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={seg.color}
              strokeWidth={isActive ? stroke + 6 : stroke}
              strokeDasharray={dasharray}
              strokeDashoffset={dashoffset}
              transform={`rotate(-90 ${cx} ${cy})`}
              style={{
                opacity: dim ? 0.35 : 1,
                cursor: 'pointer',
                transition: 'opacity 0.18s, stroke-width 0.18s',
              }}
              onMouseEnter={() => setHovered(seg.key)}
            />
          );
        })}
        <text
          x="50%"
          y={centerLabel ? '46%' : '50%'}
          dominantBaseline="middle"
          textAnchor="middle"
          className="font-bold pointer-events-none"
          style={{ fontSize: 26, fill: centerColor, transition: 'fill 0.18s' }}
        >
          {centerNumber}
        </text>
        {centerLabel && (
          <text
            x="50%"
            y="60%"
            dominantBaseline="middle"
            textAnchor="middle"
            className="pointer-events-none capitalize"
            style={{ fontSize: 11, fill: '#64748b' }}
          >
            {centerLabel}
            {centerNumber === 1 ? '' : 's'}
          </text>
        )}
      </svg>

      <div className="mt-4 flex flex-wrap justify-center gap-x-5 gap-y-2 text-xs text-slate-600">
        {segments.map((seg) => (
          <span
            key={seg.key}
            onMouseEnter={() => setHovered(seg.key)}
            onMouseLeave={() => setHovered(null)}
            className={`inline-flex items-center gap-1.5 cursor-pointer transition ${
              hovered && hovered !== seg.key ? 'opacity-50' : 'opacity-100'
            }`}
          >
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ background: seg.color }}
            />
            {seg.label} <span className="text-slate-400">({seg.value})</span>
          </span>
        ))}
      </div>
      <div className="mt-3 text-sm text-slate-500">Total experiences: {total}</div>
    </div>
  );
}

function RoleBar({ role }) {
  const pct = Math.max(0, Math.min(100, Math.round(role.score || role.confidence || 0)));
  const tone =
    pct >= 70 ? 'from-emerald-500 to-emerald-600'
      : pct >= 50 ? 'from-indigo-500 to-purple-600'
      : 'from-amber-500 to-orange-500';
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-800">{role.role}</span>
        <span className="font-semibold text-slate-700">{pct}%</span>
      </div>
      <div className="mt-1.5 h-2.5 w-full bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${tone} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function SkillsBlocks({ grouped }) {
  const groups = [
    { title: 'Programming Languages', items: grouped.programming, tone: 'indigo' },
    { title: 'Frameworks & Tools', items: grouped.frameworks_tools, tone: 'purple' },
    { title: 'Other Skills', items: grouped.other, tone: 'pink' },
  ].filter((g) => (g.items || []).length > 0);

  if (groups.length === 0) {
    return <p className="text-sm text-slate-400 mt-2">No skills extracted.</p>;
  }

  const chipTone = {
    indigo: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
    purple: 'bg-purple-50 text-purple-700 ring-purple-200',
    pink: 'bg-pink-50 text-pink-700 ring-pink-200',
  };

  return (
    <div className="space-y-5 mt-2">
      {groups.map((g) => (
        <div key={g.title}>
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            {g.title}
          </div>
          <div className="flex flex-wrap gap-2">
            {g.items.map((s) => (
              <span
                key={s}
                className={`inline-flex items-center gap-1 rounded-md ring-1 px-2.5 py-1 text-xs font-medium ${chipTone[g.tone]}`}
              >
                <CheckCircle2 className="h-3 w-3" />
                {s}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ProjectsCard({ projects }) {
  const list = (projects || []).filter(Boolean).map((p) =>
    typeof p === 'string'
      ? { name: p, description: '', technologies: [] }
      : {
          name: (p.name || '').toString(),
          description: (p.description || '').toString(),
          technologies: Array.isArray(p.technologies) ? p.technologies : [],
        }
  ).filter((p) => p.name && p.name.toLowerCase() !== 'not specified');

  const [active, setActive] = useState(null);

  // Lock body scroll when modal open
  useEffect(() => {
    if (active) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = prev; };
    }
  }, [active]);

  return (
    <>
      <Card className="p-6">
        <CardHeader
          title="Projects"
          icon={<Folder className="h-4 w-4 text-indigo-500" />}
          subtitle={`${list.length} project${list.length === 1 ? '' : 's'} extracted`}
        />
        {list.length === 0 ? (
          <p className="text-sm text-slate-400 mt-1">No projects detected</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {list.map((proj, i) => {
              const hasDetails = !!(proj.description || (proj.technologies && proj.technologies.length));
              return (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
                  {hasDetails ? (
                    <button
                      type="button"
                      onClick={() => setActive(proj)}
                      className="text-left text-slate-700 hover:text-indigo-600 hover:underline transition-colors"
                    >
                      {proj.name}
                    </button>
                  ) : (
                    <span className="text-slate-700">{proj.name}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
        {list.length > 0 && (
          <p className="mt-3 text-xs text-slate-400">Click a project title to view details</p>
        )}
      </Card>

      {active && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={() => setActive(null)}
        >
          <div
            className="relative w-full max-w-2xl rounded-2xl bg-white shadow-2xl border border-slate-200"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setActive(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 hover:text-slate-700 z-10"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="px-7 pt-7 pb-4 border-b border-slate-100">
              <div className="flex items-start gap-3 pr-10">
                <div className="mt-1 h-9 w-9 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
                  <Folder className="h-5 w-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-xl font-semibold text-slate-900 leading-snug break-words">
                    {active.name}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">Project details</p>
                </div>
              </div>
            </div>

            <div className="px-7 py-6 space-y-6">
              <section>
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2.5">
                  Description
                </h4>
                {active.description ? (
                  <p className="text-[15px] text-slate-700 leading-7 whitespace-pre-line break-words">
                    {active.description}
                  </p>
                ) : (
                  <p className="text-sm text-slate-400 italic">
                    No description was extracted from your resume for this project.
                  </p>
                )}
              </section>

              <section>
                <h4 className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2.5 flex items-center gap-1.5">
                  <Code2 className="h-3.5 w-3.5" /> Technologies
                </h4>
                {active.technologies && active.technologies.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {active.technologies.map((tech, i) => (
                      <span
                        key={i}
                        className="px-3 py-1.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100"
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400 italic">
                    No specific technologies detected.
                  </p>
                )}
              </section>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ListCard({ title, icon, items, emptyText }) {
  const list = (items || []).filter(Boolean);
  return (
    <Card className="p-6">
      <CardHeader title={title} icon={icon} subtitle={`${list.length} items`} />
      {list.length === 0 ? (
        <p className="text-sm text-slate-400 mt-1">{emptyText}</p>
      ) : (
        <ul className="mt-2 space-y-2">
          {list.slice(0, 8).map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
              <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-indigo-400 flex-shrink-0" />
              <span>{typeof item === 'string' ? item : JSON.stringify(item)}</span>
            </li>
          ))}
          {list.length > 8 && (
            <li className="text-xs text-slate-400">+ {list.length - 8} more…</li>
          )}
        </ul>
      )}
    </Card>
  );
}
