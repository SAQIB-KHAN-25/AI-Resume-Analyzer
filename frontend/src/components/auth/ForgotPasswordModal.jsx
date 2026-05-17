import React, { useEffect, useRef, useState } from 'react';
import {
  X, Mail, Lock, Eye, EyeOff, Loader2, ArrowLeft, CheckCircle2, KeyRound,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  forgotPasswordRequest,
  verifyOtpRequest,
  resetPasswordRequest,
} from '../../services/api';

const STEP_EMAIL = 'email';
const STEP_OTP = 'otp';
const STEP_PASSWORD = 'password';
const STEP_DONE = 'done';

const OTP_LENGTH = 6;

export default function ForgotPasswordModal({ initialEmail = '', onClose, onResetComplete }) {
  const [step, setStep] = useState(STEP_EMAIL);
  const [email, setEmail] = useState(initialEmail);
  const [resetToken, setResetToken] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  const handleClose = () => {
    if (submitting) return;
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={handleClose}
    >
      <div
        className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={handleClose}
          disabled={submitting}
          className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 disabled:opacity-50"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="p-6 sm:p-7">
          {step === STEP_EMAIL && (
            <EmailStep
              email={email}
              setEmail={setEmail}
              submitting={submitting}
              setSubmitting={setSubmitting}
              onNext={() => setStep(STEP_OTP)}
            />
          )}
          {step === STEP_OTP && (
            <OtpStep
              email={email}
              submitting={submitting}
              setSubmitting={setSubmitting}
              onBack={() => setStep(STEP_EMAIL)}
              onNext={(token) => {
                setResetToken(token);
                setStep(STEP_PASSWORD);
              }}
            />
          )}
          {step === STEP_PASSWORD && (
            <PasswordStep
              resetToken={resetToken}
              submitting={submitting}
              setSubmitting={setSubmitting}
              onDone={() => setStep(STEP_DONE)}
            />
          )}
          {step === STEP_DONE && (
            <DoneStep
              email={email}
              onContinue={() => {
                onResetComplete?.(email);
                onClose();
              }}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Step 1 — Email
// ────────────────────────────────────────────────────────────────────────────
function EmailStep({ email, setEmail, submitting, setSubmitting, onNext }) {
  const handleSubmit = async (e) => {
    e.preventDefault();
    const trimmed = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      toast.error('Please enter a valid email');
      return;
    }
    setSubmitting(true);
    try {
      const data = await forgotPasswordRequest(trimmed);
      if (data.email_registered === false) {
        toast.error('No account found with that email');
        return;
      }
      if (!data.delivered) {
        toast('Email server not configured — check the backend logs for the OTP.', {
          icon: 'ℹ️',
          duration: 5000,
        });
      } else {
        toast.success('Verification code sent. Check your inbox.');
      }
      onNext();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not send verification code';
      toast.error(typeof msg === 'string' ? msg : 'Could not send verification code');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
          <KeyRound className="h-5 w-5" />
        </div>
        <div className="pr-8">
          <h3 className="text-lg font-semibold text-slate-900">Reset your password</h3>
          <p className="text-sm text-slate-500 mt-1">
            Enter your registered email and we&apos;ll send a 6-digit verification code.
          </p>
        </div>
      </div>

      <div className="mt-5">
        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
          Email
        </label>
        <div className="relative">
          <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={submitting}
            autoFocus
            className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-slate-200 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none disabled:bg-slate-50"
            placeholder="you@example.com"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 text-white py-2.5 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
        {submitting ? 'Sending code…' : 'Send verification code'}
      </button>
    </form>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Step 2 — OTP
// ────────────────────────────────────────────────────────────────────────────
function OtpStep({ email, submitting, setSubmitting, onBack, onNext }) {
  const [digits, setDigits] = useState(Array(OTP_LENGTH).fill(''));
  const [resending, setResending] = useState(false);
  const [cooldown, setCooldown] = useState(60);
  const inputsRef = useRef([]);

  // Cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => Math.max(0, c - 1)), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  // Autofocus first input
  useEffect(() => {
    inputsRef.current[0]?.focus();
  }, []);

  const otpValue = digits.join('');

  const setDigitAt = (idx, val) => {
    setDigits((prev) => {
      const next = [...prev];
      next[idx] = val;
      return next;
    });
  };

  const handleChange = (idx, e) => {
    const raw = e.target.value.replace(/\D/g, '');
    if (!raw) {
      setDigitAt(idx, '');
      return;
    }
    // Pasting multiple digits
    if (raw.length > 1) {
      const chars = raw.slice(0, OTP_LENGTH - idx).split('');
      setDigits((prev) => {
        const next = [...prev];
        chars.forEach((c, i) => { next[idx + i] = c; });
        return next;
      });
      const last = Math.min(idx + chars.length, OTP_LENGTH - 1);
      inputsRef.current[last]?.focus();
      return;
    }
    setDigitAt(idx, raw);
    if (idx < OTP_LENGTH - 1) inputsRef.current[idx + 1]?.focus();
  };

  const handleKeyDown = (idx, e) => {
    if (e.key === 'Backspace' && !digits[idx] && idx > 0) {
      inputsRef.current[idx - 1]?.focus();
      setDigitAt(idx - 1, '');
    }
    if (e.key === 'ArrowLeft' && idx > 0) inputsRef.current[idx - 1]?.focus();
    if (e.key === 'ArrowRight' && idx < OTP_LENGTH - 1) inputsRef.current[idx + 1]?.focus();
  };

  const handlePaste = (e) => {
    const text = (e.clipboardData?.getData('text') || '').replace(/\D/g, '').slice(0, OTP_LENGTH);
    if (!text) return;
    e.preventDefault();
    const next = Array(OTP_LENGTH).fill('');
    text.split('').forEach((c, i) => { next[i] = c; });
    setDigits(next);
    inputsRef.current[Math.min(text.length, OTP_LENGTH - 1)]?.focus();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (otpValue.length !== OTP_LENGTH) {
      toast.error(`Please enter all ${OTP_LENGTH} digits`);
      return;
    }
    setSubmitting(true);
    try {
      const data = await verifyOtpRequest(email, otpValue);
      if (data?.reset_token) {
        toast.success('Code verified');
        onNext(data.reset_token);
      } else {
        toast.error('Verification failed');
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Invalid code';
      toast.error(typeof msg === 'string' ? msg : 'Invalid code');
      setDigits(Array(OTP_LENGTH).fill(''));
      inputsRef.current[0]?.focus();
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (cooldown > 0 || resending) return;
    setResending(true);
    try {
      const data = await forgotPasswordRequest(email);
      if (!data.delivered) {
        toast('Code re-issued — check the backend logs (SMTP not configured).', { icon: 'ℹ️' });
      } else {
        toast.success('A new code has been sent');
      }
      setCooldown(data.resend_cooldown_seconds || 60);
      setDigits(Array(OTP_LENGTH).fill(''));
      inputsRef.current[0]?.focus();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not resend';
      toast.error(typeof msg === 'string' ? msg : 'Could not resend');
    } finally {
      setResending(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <button
        type="button"
        onClick={onBack}
        disabled={submitting}
        className="inline-flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 disabled:opacity-50"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Change email
      </button>

      <div className="mt-3 flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
          <KeyRound className="h-5 w-5" />
        </div>
        <div className="pr-8">
          <h3 className="text-lg font-semibold text-slate-900">Enter verification code</h3>
          <p className="text-sm text-slate-500 mt-1 break-all">
            We sent a 6-digit code to <span className="font-medium text-slate-700">{email}</span>.
          </p>
        </div>
      </div>

      <div className="mt-5 flex justify-center gap-2" onPaste={handlePaste}>
        {digits.map((d, i) => (
          <input
            key={i}
            ref={(el) => { inputsRef.current[i] = el; }}
            type="text"
            inputMode="numeric"
            maxLength={OTP_LENGTH}
            value={d}
            onChange={(e) => handleChange(i, e)}
            onKeyDown={(e) => handleKeyDown(i, e)}
            disabled={submitting}
            className="h-12 w-11 text-center text-lg font-semibold rounded-lg border border-slate-200 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none disabled:bg-slate-50"
          />
        ))}
      </div>

      <div className="mt-3 text-center text-xs text-slate-500">
        Didn&apos;t receive a code?{' '}
        {cooldown > 0 ? (
          <span className="text-slate-400">Resend in {cooldown}s</span>
        ) : (
          <button
            type="button"
            onClick={handleResend}
            disabled={resending || submitting}
            className="text-indigo-600 hover:text-indigo-700 font-medium disabled:opacity-50"
          >
            {resending ? 'Sending…' : 'Resend code'}
          </button>
        )}
      </div>

      <button
        type="submit"
        disabled={submitting || otpValue.length !== OTP_LENGTH}
        className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 text-white py-2.5 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
        {submitting ? 'Verifying…' : 'Verify code'}
      </button>
    </form>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Step 3 — New password
// ────────────────────────────────────────────────────────────────────────────
function PasswordStep({ resetToken, submitting, setSubmitting, onDone }) {
  const [pwd, setPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);

  const checks = {
    length: pwd.length >= 8,
    upper: /[A-Z]/.test(pwd),
    lower: /[a-z]/.test(pwd),
    digit: /\d/.test(pwd),
    special: /[^A-Za-z0-9]/.test(pwd),
    match: pwd && pwd === confirm,
  };
  const allGood = Object.values(checks).every(Boolean);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!allGood) {
      toast.error('Please satisfy all password requirements');
      return;
    }
    setSubmitting(true);
    try {
      await resetPasswordRequest(resetToken, pwd);
      onDone();
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not reset password';
      toast.error(typeof msg === 'string' ? msg : 'Could not reset password');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="flex items-start gap-3">
        <div className="h-10 w-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center flex-shrink-0">
          <Lock className="h-5 w-5" />
        </div>
        <div className="pr-8">
          <h3 className="text-lg font-semibold text-slate-900">Set a new password</h3>
          <p className="text-sm text-slate-500 mt-1">
            Choose a strong password you don&apos;t use elsewhere.
          </p>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        <PwdField
          label="New password"
          show={show}
          setShow={setShow}
          value={pwd}
          onChange={setPwd}
          disabled={submitting}
          autoFocus
        />
        <PwdField
          label="Confirm password"
          show={show}
          setShow={setShow}
          value={confirm}
          onChange={setConfirm}
          disabled={submitting}
        />
      </div>

      <ul className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
        <Check ok={checks.length} text="At least 8 characters" />
        <Check ok={checks.upper} text="Uppercase letter" />
        <Check ok={checks.lower} text="Lowercase letter" />
        <Check ok={checks.digit} text="Number" />
        <Check ok={checks.special} text="Special character" />
        <Check ok={checks.match} text="Passwords match" />
      </ul>

      <button
        type="submit"
        disabled={submitting || !allGood}
        className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 text-white py-2.5 text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
      >
        {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
        {submitting ? 'Resetting…' : 'Reset password'}
      </button>
    </form>
  );
}

function PwdField({ label, show, setShow, value, onChange, disabled, autoFocus }) {
  return (
    <div>
      <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
        {label}
      </label>
      <div className="relative">
        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          autoFocus={autoFocus}
          className="w-full pl-9 pr-10 py-2.5 rounded-lg border border-slate-200 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none disabled:bg-slate-50"
          placeholder="••••••••"
        />
        <button
          type="button"
          onClick={() => setShow((s) => !s)}
          tabIndex={-1}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function Check({ ok, text }) {
  return (
    <li className={`flex items-center gap-1.5 ${ok ? 'text-emerald-600' : 'text-slate-400'}`}>
      <CheckCircle2 className={`h-3.5 w-3.5 ${ok ? '' : 'opacity-40'}`} />
      <span>{text}</span>
    </li>
  );
}

// ────────────────────────────────────────────────────────────────────────────
// Step 4 — Done
// ────────────────────────────────────────────────────────────────────────────
function DoneStep({ email, onContinue }) {
  return (
    <div className="text-center py-3">
      <div className="mx-auto h-14 w-14 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
        <CheckCircle2 className="h-7 w-7" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-slate-900">Password reset successful</h3>
      <p className="mt-1.5 text-sm text-slate-500">
        You can now sign in to{' '}
        <span className="font-medium text-slate-700 break-all">{email}</span>{' '}
        with your new password.
      </p>
      <button
        type="button"
        onClick={onContinue}
        className="mt-5 w-full inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 text-white py-2.5 text-sm font-semibold hover:bg-indigo-700"
      >
        Continue to Sign In
      </button>
    </div>
  );
}
