import React, { useEffect, useMemo, useState } from 'react';
import { History as HistoryIcon, Download, FileSearch, Trash2, AlertTriangle, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { Card, CardHeader, EmptyState, Spinner, Badge } from '../components/ui';
import PageHeader from '../components/layout/PageHeader';
import {
  getAnalysisHistory,
  downloadAnalysisReport,
  deleteAnalysisHistoryItem,
  deleteAnalysisHistoryBulk,
} from '../services/api';

export default function History({ onNavigate }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(() => new Set());
  const [confirm, setConfirm] = useState(null); // { mode: 'one'|'bulk'|'all', ids?: [] }
  const [deleting, setDeleting] = useState(false);

  const refresh = () => {
    setLoading(true);
    getAnalysisHistory()
      .then((d) => setItems(d.history || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refresh();
  }, []);

  const allChecked = items.length > 0 && selected.size === items.length;
  const someChecked = selected.size > 0 && !allChecked;

  const toggleOne = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected((prev) =>
      prev.size === items.length ? new Set() : new Set(items.map((h) => h.analysis_id))
    );
  };

  const download = async (id) => {
    try {
      const blob = await downloadAnalysisReport(id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `report_${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Failed to download report');
    }
  };

  const performDelete = async () => {
    if (!confirm) return;
    setDeleting(true);
    try {
      if (confirm.mode === 'one') {
        await deleteAnalysisHistoryItem(confirm.ids[0]);
      } else if (confirm.mode === 'all') {
        await deleteAnalysisHistoryBulk({ all: true });
      } else {
        await deleteAnalysisHistoryBulk({ ids: confirm.ids });
      }
      toast.success(
        confirm.mode === 'all'
          ? 'All history cleared'
          : `${confirm.ids.length} item${confirm.ids.length === 1 ? '' : 's'} deleted`
      );
      setSelected(new Set());
      setConfirm(null);
      refresh();
    } catch {
      toast.error('Failed to delete');
    } finally {
      setDeleting(false);
    }
  };

  const scoreTone = (s) => (s >= 80 ? 'green' : s >= 65 ? 'blue' : s >= 50 ? 'amber' : 'red');

  const subtitle = useMemo(() => {
    if (selected.size > 0) return `${selected.size} of ${items.length} selected`;
    return `${items.length} total`;
  }, [selected, items.length]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="History"
        icon={HistoryIcon}
        title="Analysis History"
        subtitle="All your past resume + JD analyses, latest first."
        actions={
          items.length > 0 ? (
            <>
              {selected.size > 0 && (
                <button
                  onClick={() => setConfirm({ mode: 'bulk', ids: Array.from(selected) })}
                  className="btn-danger btn-sm"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete selected ({selected.size})
                </button>
              )}
              <button
                onClick={() => setConfirm({ mode: 'all' })}
                className="btn-secondary btn-sm"
                title="Delete all history"
              >
                <Trash2 className="h-4 w-4" />
                Clear all
              </button>
            </>
          ) : null
        }
      />

      <Card className="p-6">
        <CardHeader title="Saved analyses" subtitle={subtitle} />
        {loading ? (
          <div className="flex justify-center py-12 text-slate-400"><Spinner size={6} /></div>
        ) : items.length === 0 ? (
          <EmptyState
            icon={HistoryIcon}
            title="No history yet"
            description="Run your first analysis to see results saved here."
            action={
              <button onClick={() => onNavigate('analyze')} className="btn-primary">
                <FileSearch className="h-4 w-4" /> New analysis
              </button>
            }
          />
        ) : (
          <div className="overflow-x-auto -mx-2">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500 border-b border-slate-200">
                  <th className="px-2 py-2.5 w-8">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                      checked={allChecked}
                      ref={(el) => { if (el) el.indeterminate = someChecked; }}
                      onChange={toggleAll}
                      aria-label="Select all"
                    />
                  </th>
                  <th className="px-2 py-2.5">Date</th>
                  <th className="px-2 py-2.5">Match</th>
                  <th className="px-2 py-2.5">ATS</th>
                  <th className="px-2 py-2.5">Top Role</th>
                  <th className="px-2 py-2.5">Missing skills</th>
                  <th className="px-2 py-2.5"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((h) => {
                  const isSel = selected.has(h.analysis_id);
                  return (
                    <tr
                      key={h.analysis_id}
                      className={`hover:bg-slate-50/60 ${isSel ? 'bg-brand-50/40' : ''}`}
                    >
                      <td className="px-2 py-3">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                          checked={isSel}
                          onChange={() => toggleOne(h.analysis_id)}
                          aria-label="Select row"
                        />
                      </td>
                      <td className="px-2 py-3 text-slate-600 whitespace-nowrap">
                        {new Date(h.created_at).toLocaleString()}
                      </td>
                      <td className="px-2 py-3">
                        <Badge tone={scoreTone(h.match_score)}>{Math.round(h.match_score)}%</Badge>
                      </td>
                      <td className="px-2 py-3">
                        <Badge tone={scoreTone(h.ats_score)}>{Math.round(h.ats_score)}%</Badge>
                      </td>
                      <td className="px-2 py-3 text-slate-700">
                        {h.predicted_roles?.[0]?.role || '—'}
                      </td>
                      <td className="px-2 py-3 text-slate-600">
                        {(h.missing_skills || []).slice(0, 3).join(', ') || '—'}
                        {h.missing_skills?.length > 3 && (
                          <span className="text-slate-400"> +{h.missing_skills.length - 3}</span>
                        )}
                      </td>
                      <td className="px-2 py-3 text-right whitespace-nowrap">
                        <button
                          onClick={() => download(h.analysis_id)}
                          className="btn-ghost text-brand-600 hover:bg-brand-50 px-2 py-1.5"
                          title="Download report"
                        >
                          <Download className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => setConfirm({ mode: 'one', ids: [h.analysis_id] })}
                          className="btn-ghost text-red-600 hover:bg-red-50 px-2 py-1.5 ml-1"
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {confirm && (
        <ConfirmDialog
          mode={confirm.mode}
          count={confirm.mode === 'all' ? items.length : (confirm.ids?.length || 0)}
          onCancel={() => !deleting && setConfirm(null)}
          onConfirm={performDelete}
          deleting={deleting}
        />
      )}
    </div>
  );
}

function ConfirmDialog({ mode, count, onCancel, onConfirm, deleting }) {
  const title =
    mode === 'all' ? 'Clear all history?' :
    mode === 'one' ? 'Delete this analysis?' :
    `Delete ${count} selected analyses?`;
  const message =
    mode === 'all'
      ? `This will permanently remove all ${count} saved ${count === 1 ? 'analysis' : 'analyses'}. This action cannot be undone.`
      : `This will permanently remove ${count} ${count === 1 ? 'analysis' : 'analyses'} from your history. This action cannot be undone.`;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
      onClick={onCancel}
    >
      <div
        className="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          onClick={onCancel}
          disabled={deleting}
          className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-slate-100 text-slate-500 disabled:opacity-50"
          aria-label="Close"
        >
          <X className="h-5 w-5" />
        </button>
        <div className="p-6">
          <div className="flex items-start gap-3">
            <div className="h-10 w-10 rounded-lg bg-red-100 text-red-600 flex items-center justify-center flex-shrink-0">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div className="min-w-0 pr-8">
              <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
              <p className="text-sm text-slate-600 mt-1.5 leading-relaxed">{message}</p>
            </div>
          </div>
          <div className="flex justify-end gap-2 mt-6">
            <button
              type="button"
              onClick={onCancel}
              disabled={deleting}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={deleting}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? <Spinner size={4} /> : <Trash2 className="h-4 w-4" />}
              {deleting ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
