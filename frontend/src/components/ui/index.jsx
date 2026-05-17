import React from 'react';
import clsx from 'clsx';

// -------- Card --------
export const Card = ({ className, children, ...props }) => (
  <div className={clsx('card', className)} {...props}>{children}</div>
);

export const CardHeader = ({ title, subtitle, action, right, icon }) => (
  <div className="flex items-start justify-between gap-4 mb-4">
    <div className="min-w-0">
      <h3 className="text-base font-semibold text-slate-900 flex items-center gap-2">
        {icon}
        <span className="truncate">{title}</span>
      </h3>
      {subtitle && <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>}
    </div>
    {action || right}
  </div>
);

// -------- ProgressBar --------
export const ProgressBar = ({ value = 0, max = 100, color = 'brand', size = 'md' }) => {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const colorMap = {
    brand: 'bg-brand-600',
    green: 'bg-emerald-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
    blue: 'bg-blue-500',
  };
  const heightMap = { sm: 'h-1.5', md: 'h-2', lg: 'h-3' };
  return (
    <div className={clsx('w-full bg-slate-100 rounded-full overflow-hidden', heightMap[size])}>
      <div
        className={clsx('h-full rounded-full transition-all duration-500', colorMap[color])}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
};

// -------- ScoreCard --------
const scoreColor = (score) => {
  if (score >= 80) return 'green';
  if (score >= 65) return 'brand';
  if (score >= 50) return 'amber';
  return 'red';
};

const scoreLabel = (score) => {
  if (score >= 80) return 'Excellent';
  if (score >= 65) return 'Good';
  if (score >= 50) return 'Moderate';
  return 'Needs Work';
};

export const ScoreCard = ({ title, score = 0, icon: Icon, description }) => {
  const color = scoreColor(score);
  const colorText = {
    brand: 'text-brand-700',
    green: 'text-emerald-600',
    amber: 'text-amber-600',
    red: 'text-red-600',
  }[color];

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          {Icon && (
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50 text-brand-600">
              <Icon className="h-5 w-5" />
            </span>
          )}
          <h3 className="text-sm font-medium text-slate-600">{title}</h3>
        </div>
        <span className={clsx('badge-slate', colorText)}>{scoreLabel(score)}</span>
      </div>
      <div className="flex items-baseline gap-2 mb-3">
        <span className={clsx('text-4xl font-bold tracking-tight', colorText)}>
          {Math.round(score)}
        </span>
        <span className="text-sm text-slate-500">/ 100</span>
      </div>
      <ProgressBar value={score} color={color} />
      {description && <p className="text-xs text-slate-500 mt-3">{description}</p>}
    </Card>
  );
};

// -------- Badge --------
export const Badge = ({ tone = 'slate', children }) => (
  <span className={`badge-${tone}`}>{children}</span>
);

// -------- EmptyState --------
export const EmptyState = ({ icon: Icon, title, description, action }) => (
  <div className="text-center py-12">
    {Icon && (
      <div className="mx-auto h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
        <Icon className="h-6 w-6" />
      </div>
    )}
    <h3 className="mt-4 text-sm font-semibold text-slate-900">{title}</h3>
    {description && <p className="mt-1 text-sm text-slate-500 max-w-sm mx-auto">{description}</p>}
    {action && <div className="mt-6">{action}</div>}
  </div>
);

// -------- Spinner --------
export const Spinner = ({ size = 5, className }) => (
  <svg
    className={clsx(`animate-spin h-${size} w-${size} text-current`, className)}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
  >
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);
