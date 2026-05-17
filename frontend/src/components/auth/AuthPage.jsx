import React, { useState, useEffect } from 'react';
import {
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  Zap,
  GraduationCap,
  Briefcase,
  Lock as LockIcon,
  Sparkles,
  ArrowRight,
  Target,
  FileText,
  Download,
  BarChart3,
  ArrowUp,
} from 'lucide-react';
import toast from 'react-hot-toast';
import api, { setAuthToken } from '../../services/api';
import ForgotPasswordModal from './ForgotPasswordModal';

export default function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState('signin');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm_password: '' });
  const [showScrollTop, setShowScrollTop] = useState(false);

  // Track window scroll for the scroll-to-top button
  useEffect(() => {
    const onScroll = () => setShowScrollTop(window.scrollY > 300);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);
  const [forgotOpen, setForgotOpen] = useState(false);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  // Password strength (0-4) — used on signup only
  const pwStrength = React.useMemo(() => {
    const p = form.password || '';
    if (!p) return 0;
    let s = 0;
    if (p.length >= 8) s++;
    if (/[A-Z]/.test(p) && /[a-z]/.test(p)) s++;
    if (/\d/.test(p)) s++;
    if (/[^A-Za-z0-9]/.test(p)) s++;
    return s;
  }, [form.password]);

  const submit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password || (mode === 'signup' && !form.full_name)) {
      toast.error('Please fill all required fields');
      return;
    }
    if (form.password.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }
    if (mode === 'signup' && form.password !== form.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }
    setLoading(true);
    try {
      const endpoint = mode === 'signin' ? '/auth/login' : '/auth/register';
      const payload =
        mode === 'signin'
          ? { email: form.email, password: form.password }
          : { full_name: form.full_name, email: form.email, password: form.password };
      const { data } = await api.post(endpoint, payload);
      localStorage.setItem('user', JSON.stringify(data.user));
      setAuthToken(data.access_token);
      toast.success(mode === 'signin' ? 'Welcome back!' : 'Account created!');
      onAuthSuccess && onAuthSuccess();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Something went wrong';
      toast.error(typeof msg === 'string' ? msg : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const switchMode = (next) => {
    setMode(next);
    document.getElementById('auth-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };
  const scrollToAuth = () => switchMode('signup');

  return (
    <div className="min-h-screen bg-white">
      {/* ===== Top header ===== */}
      <header className="absolute top-0 left-0 right-0 z-20 px-6 md:px-12 py-5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-accent-600 text-white shadow-glow">
            <Sparkles className="h-5 w-5" />
          </span>
          <span className="text-base font-semibold text-slate-900 tracking-tight">ResuMatch AI</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => switchMode('signin')}
            className={mode === 'signin' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
          >
            Sign In
          </button>
          <button
            onClick={() => switchMode('signup')}
            className={mode === 'signup' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
          >
            Sign Up
          </button>
        </div>
      </header>

      {/* ===== Hero ===== */}
      <section className="relative overflow-hidden">
        {/* Soft pastel base */}
        <div
          className="absolute inset-0 -z-20 pointer-events-none"
          style={{
            background:
              'linear-gradient(135deg, #f8fafc 0%, #eef2ff 35%, #f5f3ff 70%, #fdf4ff 100%)',
          }}
        />
        {/* Subtle dot grid */}
        <div
          className="absolute inset-0 -z-10 pointer-events-none opacity-40"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(99,102,241,0.15) 1px, transparent 1px)',
            backgroundSize: '24px 24px',
          }}
        />
        {/* Color glows */}
        <div className="absolute -top-24 -left-24 w-[28rem] h-[28rem] rounded-full bg-indigo-300/40 blur-3xl pointer-events-none" />
        <div className="absolute top-32 right-0 w-[26rem] h-[26rem] rounded-full bg-purple-300/30 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 left-1/3 w-[24rem] h-[24rem] rounded-full bg-cyan-200/40 blur-3xl pointer-events-none" />

        <div className="max-w-6xl mx-auto px-4 sm:px-6 md:px-12 pt-24 sm:pt-28 pb-16 sm:pb-24 grid lg:grid-cols-2 gap-8 lg:gap-12 items-center">
          {/* Left: copy */}
          <div className="text-slate-900">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 backdrop-blur ring-1 ring-indigo-200 px-3.5 py-1.5 text-xs font-semibold text-indigo-700 shadow-sm">
              <Sparkles className="h-3.5 w-3.5" /> Powered by GPT-4 &amp; ML
            </span>
            <h2 className="mt-5 text-3xl sm:text-4xl md:text-5xl font-bold leading-tight tracking-tight">
              Analyze Your Resume with{' '}
              <span className="text-gradient">AI-Powered Intelligence</span>
            </h2>
            <p className="mt-4 sm:mt-6 text-base sm:text-lg text-slate-700 leading-relaxed max-w-lg">
              Join thousands of professionals who have improved their resumes and landed
              their dream jobs. Create your free account today and unlock AI-powered resume
              analysis.
            </p>
            <ul className="mt-6 sm:mt-8 space-y-3.5 hidden sm:block">
              {[
                'Comprehensive resume analysis',
                'Personalized recommendations',
                'Track your progress over time',
                'Industry-specific insights',
              ].map((item) => (
                <li key={item} className="flex items-center gap-3 text-slate-800">
                  <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white">
                    <CheckCircle2 className="h-4 w-4" strokeWidth={3} />
                  </span>
                  <span className="text-base font-medium">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Right: auth card */}
          <div
            id="auth-card"
            className="card-elevated p-6 sm:p-8 max-w-md w-full mx-auto lg:ml-auto animate-slide-up"
          >
            <h3 className="text-center text-3xl font-bold text-gradient">
              {mode === 'signin' ? 'Welcome Back' : 'Create Account'}
            </h3>
            <p className="text-center text-base text-slate-500 mt-2">
              {mode === 'signin'
                ? 'Sign in to access your ResuMatch AI account'
                : 'Sign up to start analyzing your resume'}
            </p>

            <form onSubmit={submit} className="mt-6 space-y-4">
              {mode === 'signup' && (
                <Field
                  label="Full name"
                  icon={User}
                  name="full_name"
                  type="text"
                  placeholder="Your name"
                  value={form.full_name}
                  onChange={onChange}
                />
              )}
              <Field
                label="Email Address"
                icon={Mail}
                name="email"
                type="email"
                placeholder="Enter your email"
                value={form.email}
                onChange={onChange}
              />
              <Field
                label="Password"
                icon={Lock}
                name="password"
                type={showPassword ? 'text' : 'password'}
                placeholder={mode === 'signup' ? 'At least 8 characters' : 'Enter your password'}
                value={form.password}
                onChange={onChange}
                trailing={
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    className="text-slate-400 hover:text-slate-600"
                    tabIndex={-1}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
              />

              {mode === 'signup' && form.password.length > 0 && (
                <PasswordStrength score={pwStrength} />
              )}

              {mode === 'signup' && (
                <Field
                  label="Confirm Password"
                  icon={Lock}
                  name="confirm_password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Re-enter your password"
                  value={form.confirm_password}
                  onChange={onChange}
                  trailing={
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword((s) => !s)}
                      className="text-slate-400 hover:text-slate-600"
                      tabIndex={-1}
                      aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    >
                      {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  }
                />
              )}

              {mode === 'signup' && form.confirm_password.length > 0 && form.password !== form.confirm_password && (
                <p className="-mt-2 text-xs font-medium text-red-600">Passwords do not match</p>
              )}
              {mode === 'signup' && form.confirm_password.length > 0 && form.password === form.confirm_password && (
                <p className="-mt-2 text-xs font-medium text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Passwords match
                </p>
              )}

              {mode === 'signin' && (
                <div className="flex items-center justify-between text-sm">
                  <label className="flex items-center gap-2 text-slate-600">
                    <input
                      type="checkbox"
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    Remember me
                  </label>
                  <button
                    type="button"
                    className="text-indigo-600 font-medium hover:text-indigo-700"
                    onClick={() => setForgotOpen(true)}
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-gradient btn-lg w-full py-3 text-base"
              >
                {loading && <Loader2 className="h-5 w-5 animate-spin" />}
                {mode === 'signin' ? 'Sign In' : 'Create account'}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>

            <div className="mt-6 text-center text-base text-slate-600">
              {mode === 'signin' ? (
                <>
                  Don&apos;t have an account?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode('signup')}
                    className="text-indigo-600 font-semibold hover:text-indigo-700"
                  >
                    Sign Up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{' '}
                  <button
                    type="button"
                    onClick={() => switchMode('signin')}
                    className="text-indigo-600 font-semibold hover:text-indigo-700"
                  >
                    Sign In
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ===== Features ===== */}
      <section className="relative py-20 px-6 md:px-12 overflow-hidden">
        {/* Aesthetic mesh background */}
        <div
          className="absolute inset-0 -z-20 pointer-events-none"
          style={{
            background:
              'linear-gradient(135deg, #ecfeff 0%, #f0f9ff 25%, #faf5ff 60%, #fdf2f8 100%)',
          }}
        />
        <div
          className="absolute inset-0 -z-10 pointer-events-none opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(99,102,241,0.18) 1px, transparent 1px)',
            backgroundSize: '22px 22px',
          }}
        />
        {/* Soft pastel glows */}
        <div className="absolute top-10 -left-20 w-[24rem] h-[24rem] rounded-full bg-cyan-200/40 blur-3xl pointer-events-none" />
        <div className="absolute top-1/2 right-0 w-[26rem] h-[26rem] rounded-full bg-pink-200/40 blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 w-[22rem] h-[22rem] rounded-full bg-purple-200/40 blur-3xl pointer-events-none" />

        <div className="max-w-6xl mx-auto relative">
          <div className="text-center max-w-2xl mx-auto">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 backdrop-blur ring-1 ring-purple-200 px-3.5 py-1.5 text-xs font-semibold text-purple-700 shadow-sm">
              <Sparkles className="h-3.5 w-3.5" /> WHY CHOOSE US
            </span>
            <h2 className="mt-4 text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900">Unlock Your Potential</h2>
            <div className="mt-4 mx-auto h-px w-24 bg-gradient-to-r from-transparent via-purple-300 to-transparent" />
            <p className="mt-5 text-lg text-slate-600">
              Join the community that&apos;s redefining career success
            </p>
          </div>

          <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            <FeatureCard
              tint="amber"
              icon={<Zap className="h-7 w-7 text-amber-500" />}
              title="Instant Analysis"
              description="Get immediate feedback on your resume with real-time parsing and analysis in under 10 seconds."
            />
            <FeatureCard
              tint="indigo"
              icon={<GraduationCap className="h-7 w-7 text-indigo-600" />}
              title="Career Growth"
              description="Identify skill gaps and get targeted learning recommendations to advance your career faster."
            />
            <FeatureCard
              tint="pink"
              icon={<Target className="h-7 w-7 text-pink-500" />}
              title="ATS Score System"
              description="Get a precise 0-100 score across keywords (45%), skills (25%), sections (15%), and experience (15%) — exactly how recruiter ATS tools rank resumes."
            />
            <FeatureCard
              tint="purple"
              icon={<Briefcase className="h-7 w-7 text-purple-600" />}
              title="Smart Job Matching"
              description="Match your profile against real job descriptions with synonym-aware skill detection and see exactly which skills you're missing."
            />
            <FeatureCard
              tint="sky"
              icon={<FileText className="h-7 w-7 text-sky-500" />}
              title="PDF Reports"
              description="Generate beautifully formatted PDF reports with scores, missing skills, and recommendations — perfect for tracking progress over time."
            />
            <FeatureCard
              tint="emerald"
              icon={<LockIcon className="h-7 w-7 text-emerald-600" />}
              title="Privacy First"
              description="Your data is encrypted and secure. We never share your personal information with third parties."
            />
          </div>
        </div>
      </section>

      {/* ===== ATS Scoring breakdown ===== */}
      <section className="relative py-20 px-6 md:px-12 bg-slate-50 overflow-hidden">
        <div
          className="absolute inset-0 pointer-events-none opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(99,102,241,0.18) 1px, transparent 1px)',
            backgroundSize: '22px 22px',
          }}
        />
        <div className="max-w-6xl mx-auto relative">
          <div className="text-center max-w-2xl mx-auto">
            <span className="inline-flex items-center gap-2 rounded-full bg-indigo-100 text-indigo-700 px-3.5 py-1.5 text-xs font-semibold">
              <BarChart3 className="h-3.5 w-3.5" /> ATS SCORING SYSTEM
            </span>
            <h2 className="mt-4 text-4xl md:text-5xl font-bold text-slate-900">
              How We Score Your Resume
            </h2>
            <p className="mt-5 text-lg text-slate-600">
              Your ATS score is calculated using the same weighted criteria recruiters use.
            </p>
          </div>

          <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-4 gap-5">
            <ScoreBreakdownCard
              weight="45%"
              title="Keyword Match"
              description="How many JD keywords appear in your resume."
              accent="from-indigo-500 to-indigo-600"
            />
            <ScoreBreakdownCard
              weight="25%"
              title="Skill Match"
              description="Technical skills alignment with required skills."
              accent="from-purple-500 to-purple-600"
            />
            <ScoreBreakdownCard
              weight="15%"
              title="Sections"
              description="Resume completeness — education, experience, projects."
              accent="from-pink-500 to-pink-600"
            />
            <ScoreBreakdownCard
              weight="15%"
              title="Experience"
              description="Years of experience vs role requirements."
              accent="from-amber-500 to-amber-600"
            />
          </div>

          <div className="mt-10 grid md:grid-cols-3 gap-5 max-w-3xl mx-auto">
            <ScoreBadge label="Excellent" range="80–100" tone="emerald" />
            <ScoreBadge label="Good" range="65–79" tone="blue" />
            <ScoreBadge label="Needs Work" range="0–64" tone="amber" />
          </div>

          <div className="mt-12 max-w-3xl mx-auto bg-white rounded-2xl p-6 ring-1 ring-slate-200/80 shadow-lg">
            <div className="flex items-start gap-4">
              <span className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-500/30">
                <Download className="h-5 w-5" />
              </span>
              <div>
                <h3 className="text-lg font-semibold text-slate-900">Download a Detailed PDF Report</h3>
                <p className="mt-1.5 text-base text-slate-600 leading-relaxed">
                  Every analysis can be exported as a polished PDF report containing your match score, ATS
                  breakdown, matched and missing skills, predicted roles, and prioritized recommendations.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===== Path to Success ===== */}
      <section className="relative py-20 px-6 md:px-12 overflow-hidden">
        <div
          className="absolute inset-0 -z-20 pointer-events-none"
          style={{
            background:
              'linear-gradient(135deg, #eef2ff 0%, #ede9fe 50%, #fdf4ff 100%)',
          }}
        />
        <div
          className="absolute inset-0 -z-10 pointer-events-none opacity-40"
          style={{
            backgroundImage:
              'radial-gradient(circle, rgba(99,102,241,0.12) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        />
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[36rem] h-[36rem] rounded-full bg-purple-300/30 blur-3xl pointer-events-none" />
        <div className="max-w-4xl mx-auto relative">
          <div className="text-center">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900">Your Path to Success</h2>
            <div className="mt-4 mx-auto h-px w-24 bg-white/60" />
            <p className="mt-5 text-lg text-slate-700">What happens after you sign in</p>
          </div>

          <div className="mt-12 space-y-5">
            <StepCard
              number="1"
              title="Complete Your Profile"
              description="Upload your resume and let our AI extract all relevant information automatically to build your professional profile."
            />
            <StepCard
              number="2"
              title="Discover Opportunities"
              description="Compare your profile against multiple job descriptions to find the perfect fit and understand your strengths."
            />
            <StepCard
              number="3"
              title="Improve & Apply"
              description="Follow personalized recommendations to enhance your resume and increase your chances of landing interviews."
            />
          </div>

          <div className="mt-12 text-center">
            <button
              onClick={scrollToAuth}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-8 py-3.5 text-base font-semibold hover:from-indigo-700 hover:to-purple-700 shadow-lg shadow-indigo-500/30 transition"
            >
              Sign Up Now <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      {forgotOpen && (
        <ForgotPasswordModal
          initialEmail={form.email}
          onClose={() => setForgotOpen(false)}
          onResetComplete={(email) => {
            setMode('signin');
            setForm((f) => ({ ...f, email, password: '' }));
            toast.success('Sign in with your new password');
          }}
        />
      )}

      {/* ===== Footer ===== */}
      <footer className="bg-slate-900 text-slate-300 py-8">
        <div className="max-w-6xl mx-auto px-6 md:px-12 flex flex-col md:flex-row md:items-center md:justify-between gap-4 text-center md:text-left">
          <div className="flex items-center justify-center md:justify-start gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
              <Sparkles className="h-4 w-4" />
            </span>
            <span className="text-white font-semibold">ResuMatch AI</span>
          </div>
          <p className="text-sm md:text-base">
            © 2026 ResuMatch AI. Powered by{' '}
            <span className="text-white font-medium">
              Advanced NLP &amp; Machine Learning Technology
            </span>
            .
          </p>
        </div>
      </footer>

      {/* ===== Scroll to top button ===== */}
      <button
        onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
        className={`fixed z-50 bottom-6 right-6 h-11 w-11 rounded-full bg-gradient-to-br from-brand-600 to-accent-600 text-white shadow-lg shadow-brand-500/30 hover:shadow-xl hover:shadow-brand-500/40 flex items-center justify-center transition-all duration-300 ease-out hover:scale-110 active:scale-95 ${
          showScrollTop
            ? 'opacity-100 translate-y-0 pointer-events-auto'
            : 'opacity-0 translate-y-4 pointer-events-none'
        }`}
        aria-label="Scroll to top"
      >
        <ArrowUp className="h-5 w-5" strokeWidth={2.5} />
      </button>
    </div>
  );
}

function Field({ label, icon: Icon, trailing, ...rest }) {
  return (
    <div>
      {label && <label className="label">{label}</label>}
      <div className="relative">
        {Icon && (
          <Icon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400 pointer-events-none" />
        )}
        <input
          className={`input py-3 text-base ${Icon ? 'pl-11' : ''} ${trailing ? 'pr-11' : ''}`}
          {...rest}
        />
        {trailing && <div className="absolute right-3 top-1/2 -translate-y-1/2">{trailing}</div>}
      </div>
    </div>
  );
}

function PasswordStrength({ score }) {
  const labels = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const tones = [
    'bg-red-500',
    'bg-orange-500',
    'bg-amber-500',
    'bg-lime-500',
    'bg-emerald-500',
  ];
  const textTones = [
    'text-red-600',
    'text-orange-600',
    'text-amber-700',
    'text-lime-700',
    'text-emerald-700',
  ];
  return (
    <div className="-mt-2" aria-live="polite">
      <div className="flex gap-1.5">
        {[0, 1, 2, 3].map((i) => (
          <div
            key={i}
            className={`h-1.5 flex-1 rounded-full transition-colors ${
              i < score ? tones[score] : 'bg-slate-200'
            }`}
          />
        ))}
      </div>
      <div className={`mt-1.5 text-xs font-medium ${textTones[score]}`}>
        Password strength: {labels[score]}
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, description, tint = 'indigo' }) {
  const tintMap = {
    indigo: 'bg-indigo-50 group-hover:bg-indigo-100',
    purple: 'bg-purple-50 group-hover:bg-purple-100',
    pink: 'bg-pink-50 group-hover:bg-pink-100',
    amber: 'bg-amber-50 group-hover:bg-amber-100',
    emerald: 'bg-emerald-50 group-hover:bg-emerald-100',
    sky: 'bg-sky-50 group-hover:bg-sky-100',
  };
  return (
    <div className="group bg-white rounded-2xl p-7 ring-1 ring-slate-200/80 shadow-sm hover:shadow-xl hover:-translate-y-1 hover:ring-slate-300 transition-all duration-300 text-center">
      <div className={`mx-auto h-16 w-16 rounded-2xl flex items-center justify-center transition-colors ${tintMap[tint] || tintMap.indigo}`}>
        {icon}
      </div>
      <h3 className="mt-5 text-xl font-semibold text-slate-900">{title}</h3>
      <div className="mx-auto mt-2.5 h-px w-12 bg-gradient-to-r from-transparent via-slate-300 to-transparent" />
      <p className="mt-3 text-base text-slate-600 leading-relaxed">{description}</p>
    </div>
  );
}

function ScoreBreakdownCard({ weight, title, description, accent }) {
  return (
    <div className="bg-white rounded-2xl p-6 ring-1 ring-slate-200/80 shadow-sm hover:shadow-lg transition">
      <div className={`inline-flex items-center justify-center rounded-lg bg-gradient-to-r ${accent} text-white px-3 py-1 text-sm font-bold shadow-md`}>
        {weight}
      </div>
      <h3 className="mt-4 text-lg font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm text-slate-600 leading-relaxed">{description}</p>
      <div className="mt-4 h-1.5 w-full bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full bg-gradient-to-r ${accent} rounded-full`} style={{ width: weight }} />
      </div>
    </div>
  );
}

function ScoreBadge({ label, range, tone }) {
  const toneMap = {
    emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    blue: 'bg-blue-50 text-blue-700 ring-blue-200',
    amber: 'bg-amber-50 text-amber-800 ring-amber-200',
  };
  return (
    <div className={`rounded-xl px-5 py-4 ring-1 text-center ${toneMap[tone]}`}>
      <div className="text-2xl font-bold tracking-tight">{range}</div>
      <div className="text-sm font-medium mt-1">{label}</div>
    </div>
  );
}

function StepCard({ number, title, description }) {
  return (
    <div className="bg-white rounded-2xl p-6 ring-1 ring-slate-200/80 shadow-lg hover:shadow-xl transition flex gap-5 items-start">
      <span className="flex-shrink-0 flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white text-lg font-bold shadow-md shadow-indigo-500/30">
        {number}
      </span>
      <div>
        <h3 className="text-lg font-semibold text-indigo-700">{title}</h3>
        <p className="mt-1.5 text-base text-slate-600 leading-relaxed">{description}</p>
      </div>
    </div>
  );
}
