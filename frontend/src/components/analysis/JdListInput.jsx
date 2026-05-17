import React from 'react';
import { Upload, FileText, Plus, Trash2, Briefcase } from 'lucide-react';
import toast from 'react-hot-toast';
import { Card, CardHeader } from '../ui';

const MAX_JDS = 5;

export const newJd = () => ({
  id: `jd-${Math.random().toString(36).slice(2, 9)}`,
  title: '',
  mode: 'paste', // 'paste' | 'upload'
  text: '',
  file: null,
});

export function validateJds(jds) {
  if (!jds.length) return 'Add at least one job description';
  for (let i = 0; i < jds.length; i++) {
    const j = jds[i];
    const label = j.title?.trim() || `JD #${i + 1}`;
    if (j.mode === 'paste') {
      if (!j.text?.trim() || j.text.trim().length < 30) {
        return `${label}: paste a longer description (min 30 chars)`;
      }
    } else if (!j.file) {
      return `${label}: upload a JD file`;
    }
  }
  return null;
}

/**
 * Editor for one or more job descriptions. Each JD has an optional title
 * and either pasted text or an uploaded file (PDF/DOCX/TXT, ≤ 5MB).
 */
export default function JdListInput({ jds, setJds, stepNumber = 2 }) {
  const update = (id, patch) => {
    setJds((prev) => prev.map((j) => (j.id === id ? { ...j, ...patch } : j)));
  };

  const remove = (id) => {
    setJds((prev) => (prev.length === 1 ? prev : prev.filter((j) => j.id !== id)));
  };

  const add = () => {
    setJds((prev) => {
      if (prev.length >= MAX_JDS) {
        toast.error(`Maximum ${MAX_JDS} job descriptions`);
        return prev;
      }
      return [...prev, newJd()];
    });
  };

  const handleFile = (id, f) => {
    if (!f) return;
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['pdf', 'docx', 'txt'].includes(ext)) {
      toast.error('JD file must be PDF, DOCX, or TXT');
      return;
    }
    if (f.size > 5 * 1024 * 1024) {
      toast.error('JD file must be ≤ 5MB');
      return;
    }
    update(id, { file: f });
  };

  return (
    <Card className="p-6">
      <CardHeader
        title={`${stepNumber}. Job Description${jds.length > 1 ? 's' : ''}`}
        subtitle={
          jds.length > 1
            ? `Comparing against ${jds.length} JDs — we'll pick your best fit`
            : 'Paste the JD or upload a file. Add more to compare across multiple jobs.'
        }
      />

      <div className="space-y-4">
        {jds.map((jd, idx) => (
          <div
            key={jd.id}
            className="rounded-xl ring-1 ring-slate-200 bg-slate-50/40 p-4"
          >
            <div className="flex items-center justify-between gap-2 mb-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                <span className="flex h-6 w-6 items-center justify-center rounded-md bg-brand-100 text-brand-700 text-xs">
                  <Briefcase className="h-3.5 w-3.5" />
                </span>
                JD #{idx + 1}
              </div>
              {jds.length > 1 && (
                <button
                  type="button"
                  onClick={() => remove(jd.id)}
                  className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                  title="Remove this JD"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>

            <div className="space-y-3">
              <input
                className="input"
                placeholder="Job title (optional, e.g. Senior Backend Engineer)"
                value={jd.title}
                onChange={(e) => update(jd.id, { title: e.target.value })}
              />

              {/* Mode tabs */}
              <div className="inline-flex rounded-lg bg-slate-100 p-1">
                {['paste', 'upload'].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => update(jd.id, { mode: m })}
                    className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${
                      jd.mode === m
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    {m === 'paste' ? 'Paste text' : 'Upload file'}
                  </button>
                ))}
              </div>

              {jd.mode === 'paste' ? (
                <>
                  <textarea
                    className="input min-h-[150px] resize-y"
                    placeholder="Paste the complete job description here…"
                    value={jd.text}
                    onChange={(e) => update(jd.id, { text: e.target.value })}
                  />
                  <div className="text-xs text-slate-500">{jd.text.length} characters</div>
                </>
              ) : (
                <label
                  htmlFor={`jd-file-${jd.id}`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    const f = e.dataTransfer.files?.[0];
                    if (f) handleFile(jd.id, f);
                  }}
                  className="block border-2 border-dashed border-slate-300 rounded-xl p-6 text-center cursor-pointer hover:border-brand-400 hover:bg-brand-50/40 transition"
                >
                  <input
                    id={`jd-file-${jd.id}`}
                    type="file"
                    accept=".pdf,.docx,.txt"
                    className="hidden"
                    onChange={(e) => e.target.files?.[0] && handleFile(jd.id, e.target.files[0])}
                  />
                  {jd.file ? (
                    <div className="flex items-center justify-center gap-3">
                      <FileText className="h-7 w-7 text-brand-600" />
                      <div className="text-left">
                        <div className="font-medium text-slate-900">{jd.file.name}</div>
                        <div className="text-xs text-slate-500">click to change</div>
                      </div>
                    </div>
                  ) : (
                    <>
                      <Upload className="mx-auto h-6 w-6 text-slate-400" />
                      <div className="mt-1.5 text-sm font-medium text-slate-900">Drop JD file</div>
                      <div className="text-xs text-slate-500">PDF, DOCX, or TXT · max 5MB</div>
                    </>
                  )}
                </label>
              )}
            </div>
          </div>
        ))}

        <button
          type="button"
          onClick={add}
          disabled={jds.length >= MAX_JDS}
          className="w-full inline-flex items-center justify-center gap-1.5 rounded-lg border border-dashed border-slate-300 py-2.5 text-sm font-medium text-brand-600 hover:bg-brand-50/40 hover:border-brand-400 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          <Plus className="h-4 w-4" />
          {jds.length >= MAX_JDS
            ? `Maximum ${MAX_JDS} JDs reached`
            : 'Add another job description'}
        </button>
      </div>
    </Card>
  );
}
