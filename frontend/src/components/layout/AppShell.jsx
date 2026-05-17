import React, { useEffect, useRef, useState } from 'react';
import clsx from 'clsx';
import {
  Home, LayoutDashboard, FileSearch, History, LogOut, Sparkles, FileText, Users,
  Pencil, X, Camera, Trash2, Loader2, Lock, Eye, EyeOff, CheckCircle2, ChevronDown, ChevronUp,
  Menu, ArrowUp,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { viewProfileResume, updateUserProfile, changePasswordRequest } from '../../services/api';
import ForgotPasswordModal from '../auth/ForgotPasswordModal';

const NAV = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'analyze', label: 'New Analysis', icon: FileSearch },
  { id: 'bulk', label: 'Compare Resumes', icon: Users },
  { id: 'history', label: 'History', icon: History },
  { id: 'view-resume', label: 'View Resume', icon: FileText, action: 'viewResume' },
];

// Bottom nav items (subset for mobile — most used tabs)
const BOTTOM_NAV = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'analyze', label: 'Analyze', icon: FileSearch },
  { id: 'history', label: 'History', icon: History },
];

export default function AppShell({ children, user, activeTab, onTabChange, onLogout, onUserUpdate }) {
  const [editing, setEditing] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const scrollRef = useRef(null);

  // Close mobile drawer when tab changes
  const handleTabChange = (id) => {
    onTabChange(id);
    setMobileOpen(false);
  };

  // Lock body scroll when mobile drawer is open
  useEffect(() => {
    if (mobileOpen) {
      const prev = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => { document.body.style.overflow = prev; };
    }
  }, [mobileOpen]);

  const handleViewResume = async () => {
    setMobileOpen(false);
    try {
      await viewProfileResume();
    } catch (e) {
      const status = e?.response?.status;
      if (status === 404) {
        toast.error('No resume uploaded yet. Upload one from the Dashboard.');
      } else {
        toast.error('Could not load resume');
      }
    }
  };

  // Shared sidebar content (used for both desktop sidebar & mobile drawer)
  const SidebarContent = ({ isMobile = false }) => (
    <>
      <div className="h-16 flex items-center gap-2.5 px-6 border-b border-slate-200/70">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-accent-600 text-white shadow-glow">
          <Sparkles className="h-4 w-4" />
        </span>
        <div className="flex flex-col leading-tight">
          <span className="font-semibold text-slate-900 text-[15px] tracking-tight">ResuMatch AI</span>
          <span className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">Intelligent Matching</span>
        </div>
        {isMobile && (
          <button
            onClick={() => setMobileOpen(false)}
            className="ml-auto p-1.5 rounded-lg hover:bg-slate-100 text-slate-500"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = !item.action && activeTab === item.id;
          const onClick = () => {
            if (item.action === 'viewResume') return handleViewResume();
            handleTabChange(item.id);
          };
          return (
            <button
              key={item.id}
              onClick={onClick}
              className={clsx('nav-link w-full', active && 'nav-link-active')}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="p-3 border-t border-slate-200">
        <button
          type="button"
          onClick={() => { setEditing(true); setMobileOpen(false); }}
          className="group w-full flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-slate-50 transition-colors text-left"
          title="Edit profile"
        >
          {user?.profile_pic ? (
            <img
              src={user.profile_pic}
              alt={user?.full_name || 'User'}
              className="h-9 w-9 rounded-full object-cover ring-1 ring-slate-200"
            />
          ) : (
            <div className="h-9 w-9 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center font-semibold text-sm">
              {user?.full_name?.charAt(0).toUpperCase() || 'U'}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-slate-900 truncate">
              {user?.full_name || 'User'}
            </div>
            <div className="text-xs text-slate-500 truncate">{user?.email}</div>
          </div>
          <Pencil className="h-3.5 w-3.5 text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
        </button>
        <button onClick={() => { onLogout(); setMobileOpen(false); }} className="nav-link w-full mt-1 text-slate-600">
          <LogOut className="h-4 w-4" />
          Log out
        </button>
      </div>
    </>
  );

  return (
    <div className="h-screen flex overflow-hidden relative bg-shell-gradient">
      {/* Decorative ambient blobs (behind everything, non-interactive) */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-32 h-[28rem] w-[28rem] rounded-full bg-brand-400/30 blur-3xl" />
        <div className="absolute top-1/3 -right-40 h-[32rem] w-[32rem] rounded-full bg-accent-400/25 blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 h-[28rem] w-[28rem] rounded-full bg-fuchsia-300/25 blur-3xl" />
      </div>

      {/* ===== Desktop Sidebar (hidden on mobile) ===== */}
      <aside className="relative z-10 w-64 bg-white/85 backdrop-blur-xl ring-1 ring-white/60 border-r border-slate-200/60 flex-shrink-0 hidden lg:flex flex-col shadow-[1px_0_20px_-10px_rgba(15,23,42,0.15)]">
        <SidebarContent />
      </aside>

      {/* ===== Mobile Drawer Overlay ===== */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
          {/* Drawer */}
          <aside
            className="relative z-50 w-72 max-w-[85vw] h-full bg-white/95 backdrop-blur-xl shadow-2xl flex flex-col animate-slide-in-left"
            onClick={(e) => e.stopPropagation()}
          >
            <SidebarContent isMobile />
          </aside>
        </div>
      )}

      {/* Main + Footer */}
      <div
        ref={scrollRef}
        className="relative z-10 flex-1 flex flex-col overflow-auto"
        onScroll={(e) => {
          const scrollY = e.currentTarget.scrollTop;
          setShowScrollTop(scrollY > 300);
        }}
      >
        {/* ===== Mobile top bar (hidden on desktop) ===== */}
        <header className="lg:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-white/90 backdrop-blur-lg border-b border-slate-200/60 shadow-soft">
          <button
            onClick={() => setMobileOpen(true)}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-700 transition"
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-accent-600 text-white">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            <span className="font-semibold text-slate-900 text-sm tracking-tight">ResuMatch AI</span>
          </div>
          <div className="ml-auto">
            <button
              onClick={() => setEditing(true)}
              className="flex items-center justify-center"
            >
              {user?.profile_pic ? (
                <img
                  src={user.profile_pic}
                  alt={user?.full_name || 'User'}
                  className="h-8 w-8 rounded-full object-cover ring-1 ring-slate-200"
                />
              ) : (
                <div className="h-8 w-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center font-semibold text-xs">
                  {user?.full_name?.charAt(0).toUpperCase() || 'U'}
                </div>
              )}
            </button>
          </div>
        </header>

        <main className="flex-1">
          <div className="page-container">{children}</div>
        </main>

        <footer className="border-t border-slate-200/60 bg-white/70 backdrop-blur-md hidden lg:block">
          <div className="max-w-6xl mx-auto px-8 py-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="flex items-center gap-2.5">
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-600 text-white">
                  <Sparkles className="h-3.5 w-3.5" />
                </span>
                <div>
                  <div className="text-sm font-semibold text-slate-900">ResuMatch AI</div>
                  <div className="text-xs text-slate-500">
                    Enterprise-grade resume parsing & intelligent job matching
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-slate-500">
                <span>© 2026 ResuMatch AI</span>
                <span className="hidden md:inline">·</span>
                <span>Powered by Advanced NLP & Machine Learning</span>
                <span className="hidden md:inline">·</span>
                <a
                  href="http://localhost:8000/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="text-brand-600 hover:text-brand-700 font-medium"
                >
                  API Docs
                </a>
              </div>
            </div>
          </div>
        </footer>

        {/* ===== Mobile bottom nav (visible on mobile only) ===== */}
        <nav className="lg:hidden sticky bottom-0 z-30 bg-white/95 backdrop-blur-lg border-t border-slate-200/60 shadow-[0_-4px_16px_-6px_rgba(15,23,42,0.1)] safe-area-bottom">
          <div className="flex items-center justify-around px-2 py-1">
            {BOTTOM_NAV.map((item) => {
              const Icon = item.icon;
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleTabChange(item.id)}
                  className={clsx(
                    'flex flex-col items-center gap-0.5 py-2 px-3 rounded-lg transition-colors min-w-0',
                    active
                      ? 'text-brand-600'
                      : 'text-slate-400 hover:text-slate-600',
                  )}
                >
                  <Icon className={clsx('h-5 w-5', active && 'text-brand-600')} />
                  <span className={clsx('text-[10px] font-medium', active && 'text-brand-600')}>
                    {item.label}
                  </span>
                </button>
              );
            })}
          </div>
        </nav>

        {/* ===== Scroll to top button ===== */}
        <button
          onClick={() => scrollRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
          className={clsx(
            'fixed z-40 bottom-20 lg:bottom-8 right-4 lg:right-8',
            'h-11 w-11 rounded-full',
            'bg-gradient-to-br from-brand-600 to-accent-600 text-white',
            'shadow-lg shadow-brand-500/30 hover:shadow-xl hover:shadow-brand-500/40',
            'flex items-center justify-center',
            'transition-all duration-300 ease-out',
            'hover:scale-110 active:scale-95',
            showScrollTop
              ? 'opacity-100 translate-y-0 pointer-events-auto'
              : 'opacity-0 translate-y-4 pointer-events-none',
          )}
          aria-label="Scroll to top"
        >
          <ArrowUp className="h-5 w-5" strokeWidth={2.5} />
        </button>
      </div>

      {editing && (
        <ProfileEditModal
          user={user}
          onClose={() => setEditing(false)}
          onSaved={(updated) => {
            onUserUpdate?.(updated);
            setEditing(false);
          }}
        />
      )}
    </div>
  );
}

function ProfileEditModal({ user, onClose, onSaved }) {
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [profilePic, setProfilePic] = useState(user?.profile_pic || null);
  const [saving, setSaving] = useState(false);
  const [resizing, setResizing] = useState(false);
  const fileRef = useRef(null);

  // Lock body scroll
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  const handlePickFile = () => fileRef.current?.click();

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be smaller than 5 MB');
      return;
    }
    setResizing(true);
    try {
      const dataUrl = await resizeImageToDataUrl(file, 256, 0.85);
      setProfilePic(dataUrl);
    } catch {
      toast.error('Could not process image');
    } finally {
      setResizing(false);
    }
  };

  const handleRemovePic = () => setProfilePic(null);

  const handleSave = async (e) => {
    e.preventDefault();
    const trimmedName = fullName.trim();
    const trimmedEmail = email.trim();
    if (trimmedName.length < 2) {
      toast.error('Name must be at least 2 characters');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      toast.error('Please enter a valid email');
      return;
    }
    setSaving(true);
    try {
      const res = await updateUserProfile(user.id, {
        full_name: trimmedName,
        email: trimmedEmail,
        profile_pic: profilePic,
      });
      const updated = res?.user || { ...user, full_name: trimmedName, email: trimmedEmail, profile_pic: profilePic };
      toast.success('Profile updated');
      onSaved(updated);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Failed to update profile';
      toast.error(typeof msg === 'string' ? msg : 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={() => !saving && onClose()}
    >
      <div
        className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-slate-200 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onClose}
          disabled={saving}
          className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 disabled:opacity-50"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>

        <form onSubmit={handleSave} className="p-6">
          <h3 className="text-lg font-semibold text-slate-900">Edit profile</h3>
          <p className="text-sm text-slate-500 mt-0.5">
            Update your name, email, and profile picture.
          </p>

          {/* Avatar */}
          <div className="mt-5 flex flex-col items-center">
            <div className="relative">
              {profilePic ? (
                <img
                  src={profilePic}
                  alt="Profile"
                  className="h-24 w-24 rounded-full object-cover ring-2 ring-slate-200"
                />
              ) : (
                <div className="h-24 w-24 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-3xl font-semibold ring-2 ring-slate-200">
                  {fullName.charAt(0).toUpperCase() || 'U'}
                </div>
              )}
              <button
                type="button"
                onClick={handlePickFile}
                disabled={resizing || saving}
                className="absolute -bottom-1 -right-1 h-9 w-9 rounded-full bg-brand-600 text-white flex items-center justify-center shadow-md hover:bg-brand-700 disabled:opacity-50"
                title="Upload new picture"
              >
                {resizing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Camera className="h-4 w-4" />}
              </button>
            </div>
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="flex items-center gap-3 mt-3 text-xs">
              <button
                type="button"
                onClick={handlePickFile}
                disabled={resizing || saving}
                className="text-brand-600 hover:text-brand-700 font-medium disabled:opacity-50"
              >
                Upload picture
              </button>
              {profilePic && (
                <>
                  <span className="text-slate-300">•</span>
                  <button
                    type="button"
                    onClick={handleRemovePic}
                    disabled={saving}
                    className="text-red-600 hover:text-red-700 font-medium inline-flex items-center gap-1 disabled:opacity-50"
                  >
                    <Trash2 className="h-3 w-3" /> Remove
                  </button>
                </>
              )}
            </div>
          </div>

          {/* Fields */}
          <div className="mt-6 space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Full name
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={saving}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none disabled:bg-slate-50"
                placeholder="Your name"
                maxLength={100}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={saving}
                className="w-full px-3 py-2 rounded-lg border border-slate-200 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none disabled:bg-slate-50"
                placeholder="you@example.com"
              />
            </div>
          </div>

          {/* Change password section */}
          <ChangePasswordSection userEmail={user?.email} disabled={saving} />

          <div className="flex justify-end gap-2 mt-6">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving || resizing}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Resize an image File to a square thumbnail (max `size` px on the longer edge,
 * cover-cropped to a square) and return a JPEG data URL.
 */
function resizeImageToDataUrl(file, size = 256, quality = 0.85) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error);
    reader.onload = () => {
      const img = new Image();
      img.onerror = () => reject(new Error('Image load failed'));
      img.onload = () => {
        const minSide = Math.min(img.width, img.height);
        const sx = (img.width - minSide) / 2;
        const sy = (img.height - minSide) / 2;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, sx, sy, minSide, minSide, 0, 0, size, size);
        try {
          resolve(canvas.toDataURL('image/jpeg', quality));
        } catch (err) {
          reject(err);
        }
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

/**
 * Collapsible change-password section embedded in the profile edit modal.
 * Self-contained — does NOT submit the outer profile form.
 */
function ChangePasswordSection({ userEmail, disabled }) {
  const [open, setOpen] = useState(false);
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);

  const checks = {
    length: newPwd.length >= 8,
    upper: /[A-Z]/.test(newPwd),
    lower: /[a-z]/.test(newPwd),
    digit: /\d/.test(newPwd),
    special: /[^A-Za-z0-9]/.test(newPwd),
    match: newPwd.length > 0 && newPwd === confirmPwd,
    different: newPwd.length > 0 && newPwd !== currentPwd,
  };
  const allGood = Object.values(checks).every(Boolean) && currentPwd.length > 0;

  const reset = () => {
    setCurrentPwd('');
    setNewPwd('');
    setConfirmPwd('');
    setShowCurrent(false);
    setShowNew(false);
  };

  const handleChange = async () => {
    if (!currentPwd) {
      toast.error('Please enter your current password');
      return;
    }
    if (!allGood) {
      toast.error('Please satisfy all password requirements');
      return;
    }
    setSubmitting(true);
    try {
      await changePasswordRequest(currentPwd, newPwd);
      toast.success('Password changed successfully');
      reset();
      setOpen(false);
    } catch (err) {
      const msg = err?.response?.data?.detail || 'Could not change password';
      toast.error(typeof msg === 'string' ? msg : 'Could not change password');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="mt-5 pt-5 border-t border-slate-200">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          disabled={disabled}
          className="w-full flex items-center justify-between group disabled:opacity-50"
        >
          <span className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <Lock className="h-4 w-4 text-slate-500" />
            Change password
          </span>
          {open ? (
            <ChevronUp className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          )}
        </button>

        {open && (
          <div className="mt-4 space-y-3">
            <PwdInput
              label="Current password"
              value={currentPwd}
              onChange={setCurrentPwd}
              show={showCurrent}
              toggleShow={() => setShowCurrent((s) => !s)}
              disabled={submitting || disabled}
              autoComplete="current-password"
            />
            <PwdInput
              label="New password"
              value={newPwd}
              onChange={setNewPwd}
              show={showNew}
              toggleShow={() => setShowNew((s) => !s)}
              disabled={submitting || disabled}
              autoComplete="new-password"
            />
            <PwdInput
              label="Confirm new password"
              value={confirmPwd}
              onChange={setConfirmPwd}
              show={showNew}
              toggleShow={() => setShowNew((s) => !s)}
              disabled={submitting || disabled}
              autoComplete="new-password"
            />

            <ul className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs pt-1">
              <StrengthCheck ok={checks.length} text="At least 8 characters" />
              <StrengthCheck ok={checks.upper} text="Uppercase letter" />
              <StrengthCheck ok={checks.lower} text="Lowercase letter" />
              <StrengthCheck ok={checks.digit} text="Number" />
              <StrengthCheck ok={checks.special} text="Special character" />
              <StrengthCheck ok={checks.match} text="Passwords match" />
              <StrengthCheck ok={checks.different} text="Different from current" />
            </ul>

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={() => setForgotOpen(true)}
                disabled={submitting || disabled}
                className="text-xs text-brand-600 hover:text-brand-700 font-medium disabled:opacity-50"
              >
                Forgot password?
              </button>
              <button
                type="button"
                onClick={handleChange}
                disabled={submitting || disabled || !allGood}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {submitting ? 'Changing…' : 'Change password'}
              </button>
            </div>
          </div>
        )}
      </div>

      {forgotOpen && (
        <ForgotPasswordModal
          initialEmail={userEmail || ''}
          onClose={() => setForgotOpen(false)}
          onResetComplete={() => {
            toast.success('Password reset. Please sign in again with your new password.');
            setForgotOpen(false);
            setOpen(false);
          }}
        />
      )}
    </>
  );
}

function PwdInput({ label, value, onChange, show, toggleShow, disabled, autoComplete }) {
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
          autoComplete={autoComplete}
          className="w-full pl-9 pr-10 py-2 rounded-lg border border-slate-200 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none disabled:bg-slate-50"
          placeholder="••••••••"
        />
        <button
          type="button"
          onClick={toggleShow}
          tabIndex={-1}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

function StrengthCheck({ ok, text }) {
  return (
    <li className={`flex items-center gap-1.5 ${ok ? 'text-emerald-600' : 'text-slate-400'}`}>
      <CheckCircle2 className={`h-3.5 w-3.5 ${ok ? '' : 'opacity-40'}`} />
      <span>{text}</span>
    </li>
  );
}
