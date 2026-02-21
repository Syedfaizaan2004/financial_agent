"use client";
import { useState } from "react";
import { Settings, Save } from "lucide-react";
import { savePreferences } from "@/lib/api";

interface UserPrefs {
    userId: string;
    riskProfile: string;
    timeHorizon: string;
    preferredMetrics: string[];
}

interface PreferencesPanelProps {
    prefs: UserPrefs;
    onChange: (p: UserPrefs) => void;
}

const METRICS = ["ROE", "FCF", "EPS", "Revenue Growth", "Net Margin", "Debt/Equity"];

export default function PreferencesPanel({ prefs, onChange }: PreferencesPanelProps) {
    const [open, setOpen] = useState(false);
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    const toggle = (m: string) => {
        const has = prefs.preferredMetrics.includes(m);
        onChange({
            ...prefs,
            preferredMetrics: has
                ? prefs.preferredMetrics.filter(x => x !== m)
                : [...prefs.preferredMetrics, m],
        });
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await savePreferences({
                user_id: prefs.userId,
                risk_profile: prefs.riskProfile,
                time_horizon: prefs.timeHorizon,
                preferred_metrics: prefs.preferredMetrics,
            });
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        } catch { /* ignore */ } finally {
            setSaving(false);
        }
    };

    return (
        <div className="relative">
            <button
                onClick={() => setOpen(o => !o)}
                className="flex items-center gap-2 btn-ghost text-xs"
            >
                <Settings size={14} /> Preferences
            </button>

            {open && (
                <div className="absolute right-0 top-10 z-50 w-72 card shadow-2xl shadow-black/60 border-brand-700/30 space-y-4 animate-fade-in">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-white">Research Preferences</span>
                        <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-white text-xs">✕</button>
                    </div>

                    {/* User ID */}
                    <div>
                        <label className="text-xs text-slate-400 mb-1 block">User ID</label>
                        <input
                            value={prefs.userId}
                            onChange={e => onChange({ ...prefs, userId: e.target.value })}
                            className="w-full bg-surface border border-surface-border rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-brand-600"
                            placeholder="e.g. analyst_1"
                        />
                    </div>

                    {/* Risk profile */}
                    <div>
                        <label className="text-xs text-slate-400 mb-1.5 block">Risk Profile</label>
                        <div className="flex gap-2">
                            {["conservative", "moderate", "aggressive"].map(rp => (
                                <button
                                    key={rp}
                                    onClick={() => onChange({ ...prefs, riskProfile: rp })}
                                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all border
                    ${prefs.riskProfile === rp
                                            ? "bg-brand-700 border-brand-600 text-white"
                                            : "bg-surface border-surface-border text-slate-400 hover:border-slate-600"}`}
                                >
                                    {rp.charAt(0).toUpperCase() + rp.slice(1)}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Time horizon */}
                    <div>
                        <label className="text-xs text-slate-400 mb-1.5 block">Time Horizon</label>
                        <div className="flex gap-2">
                            {["short", "medium", "long"].map(th => (
                                <button
                                    key={th}
                                    onClick={() => onChange({ ...prefs, timeHorizon: th })}
                                    className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all border
                    ${prefs.timeHorizon === th
                                            ? "bg-brand-700 border-brand-600 text-white"
                                            : "bg-surface border-surface-border text-slate-400 hover:border-slate-600"}`}
                                >
                                    {th.charAt(0).toUpperCase() + th.slice(1)}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Preferred metrics */}
                    <div>
                        <label className="text-xs text-slate-400 mb-1.5 block">Preferred Metrics</label>
                        <div className="flex flex-wrap gap-1.5">
                            {METRICS.map(m => (
                                <button
                                    key={m}
                                    onClick={() => toggle(m)}
                                    className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all
                    ${prefs.preferredMetrics.includes(m)
                                            ? "bg-brand-700 border-brand-600 text-white"
                                            : "border-surface-border text-slate-400 hover:border-slate-500"}`}
                                >
                                    {m}
                                </button>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className="btn-primary w-full flex items-center justify-center gap-2"
                    >
                        <Save size={13} />
                        {saving ? "Saving…" : saved ? "✓ Saved!" : "Save to Memory"}
                    </button>
                </div>
            )}
        </div>
    );
}
