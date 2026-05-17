import React from 'react';
import clsx from 'clsx';

/**
 * Consistent page header used at the top of every main page.
 *
 * Props:
 *   eyebrow  — optional small label above title (e.g. "Dashboard")
 *   title    — required page title
 *   subtitle — optional description line
 *   icon     — optional Lucide icon component (rendered in brand gradient chip)
 *   actions  — optional React node rendered on the right (buttons, filters, etc.)
 *   className
 */
export default function PageHeader({ eyebrow, title, subtitle, icon: Icon, actions, className }) {
  return (
    <header
      className={clsx(
        'flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-8',
        className,
      )}
    >
      <div className="flex items-start gap-4">
        {Icon && (
          <span className="hidden sm:flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-accent-600 text-white shadow-glow">
            <Icon className="h-5 w-5" />
          </span>
        )}
        <div className="min-w-0">
          {eyebrow && <div className="eyebrow mb-1">{eyebrow}</div>}
          <h1 className="h2 truncate">{title}</h1>
          {subtitle && <p className="subtle mt-1.5 max-w-2xl">{subtitle}</p>}
        </div>
      </div>
      {actions && (
        <div className="flex flex-wrap items-center gap-2 md:flex-shrink-0">{actions}</div>
      )}
    </header>
  );
}
