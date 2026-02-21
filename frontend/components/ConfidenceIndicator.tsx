"use client";
import { ShieldCheck, ShieldAlert, Info } from "lucide-react";
import { confidenceColor, confidenceLabel } from "@/lib/utils";
import type { Contradiction, Uncertainty } from "@/lib/types";

interface ConfidenceIndicatorProps {
    score: number;
    contradictions: Contradiction[];
    uncertainties: Uncertainty[];
}

export default function ConfidenceIndicator({
    score,
    contradictions,
    uncertainties,
}: ConfidenceIndicatorProps) {
    const pct = Math.round(score * 100);
    const color = confidenceColor(score);
    const label = confidenceLabel(score);
    const icon = score >= 0.65 ? <ShieldCheck size={16} className="text-emerald-400" /> :
        <ShieldAlert size={16} className="text-amber-400" />;

    const highSeverity = uncertainties.filter(u => u.severity === "high").length;

    return (
        <div className="card space-y-4 animate-slide-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {icon}
                    <span className="text-sm font-semibold text-white">Confidence & Transparency</span>
                </div>
                <span className={`text-xl font-bold ${score >= 0.70 ? "text-emerald-400" : score >= 0.50 ? "text-amber-400" : "text-red-400"}`}>
                    {pct}%
                </span>
            </div>

            {/* Progress bar */}
            <div>
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>{label} Confidence</span>
                    <span>{pct}/100</span>
                </div>
                <div className="h-2.5 bg-surface-border rounded-full overflow-hidden">
                    <div
                        className={`h-full ${color} rounded-full transition-all duration-700`}
                        style={{ width: `${pct}%` }}
                    />
                </div>
            </div>

            {/* Contradiction alerts */}
            {contradictions.length > 0 && (
                <div className="space-y-2">
                    <p className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
                        ⚡ Conflicting Signals ({contradictions.length})
                    </p>
                    {contradictions.slice(0, 3).map((c, i) => (
                        <div key={i} className={`rounded-xl p-3 text-xs flex gap-2 items-start
              ${c.severity === "critical" ? "bg-red-950/50 border border-red-800/50 text-red-300"
                                : "bg-amber-950/40 border border-amber-800/40 text-amber-300"}`}>
                            <span className="mt-0.5 shrink-0">{c.severity === "critical" ? "🔴" : "🟡"}</span>
                            {c.message}
                        </div>
                    ))}
                </div>
            )}

            {/* Uncertainty notes — show only high severity */}
            {highSeverity > 0 && (
                <div className="space-y-1.5">
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                        <Info size={12} /> Data Quality Notes
                    </p>
                    {uncertainties
                        .filter(u => u.severity === "high")
                        .slice(0, 3)
                        .map((u, i) => (
                            <p key={i} className="text-xs text-slate-400 flex gap-2">
                                <span className="shrink-0 text-orange-400">▸</span>
                                {u.message}
                            </p>
                        ))}
                </div>
            )}

            {contradictions.length === 0 && highSeverity === 0 && (
                <p className="text-xs text-emerald-400/80 flex items-center gap-2">
                    <span>✓</span> No contradictions or high-severity issues detected.
                </p>
            )}
        </div>
    );
}
