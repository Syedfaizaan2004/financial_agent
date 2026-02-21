"use client";
import { AlertTriangle, ShieldX, Cloud, Zap } from "lucide-react";
import type { Uncertainty, RiskData } from "@/lib/types";

interface RiskAlertsProps {
    uncertainties: Uncertainty[];
    riskData?: RiskData;
}

const SEVERITY_STYLE: Record<string, string> = {
    high: "border-red-800/60 bg-red-950/40 text-red-300",
    medium: "border-amber-800/40 bg-amber-950/30 text-amber-300",
    low: "border-slate-700/50 bg-slate-800/30 text-slate-400",
};
const SEVERITY_ICON: Record<string, React.ReactNode> = {
    high: <ShieldX size={14} className="text-red-400 shrink-0 mt-0.5" />,
    medium: <AlertTriangle size={14} className="text-amber-400 shrink-0 mt-0.5" />,
    low: <Cloud size={14} className="text-slate-400 shrink-0 mt-0.5" />,
};

export default function RiskAlerts({ uncertainties, riskData }: RiskAlertsProps) {
    const hiddenRisks = riskData?.hidden_risks ?? [];
    const hasAlerts = uncertainties.length > 0 || hiddenRisks.length > 0;

    if (!hasAlerts) {
        return (
            <div className="card border-emerald-800/30 bg-emerald-950/20">
                <div className="flex items-center gap-2 text-emerald-400 text-sm">
                    <span>✓</span>
                    <span>No significant risk alerts or data quality issues detected.</span>
                </div>
            </div>
        );
    }

    // Sort: high → medium → low
    const sorted = [...uncertainties].sort((a, b) => {
        const order = { high: 0, medium: 1, low: 2 } as Record<string, number>;
        return (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
    });

    return (
        <div className="card space-y-4 animate-slide-up">
            <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-400" />
                <h3 className="text-sm font-semibold text-white">Risk & Data Quality Alerts</h3>
                {uncertainties.filter(u => u.severity === "high").length > 0 && (
                    <span className="badge-red ml-auto">
                        {uncertainties.filter(u => u.severity === "high").length} critical
                    </span>
                )}
            </div>

            <div className="space-y-2">
                {sorted.slice(0, 5).map((u, i) => (
                    <div key={i} className={`flex gap-2.5 items-start p-3 rounded-xl border text-xs ${SEVERITY_STYLE[u.severity]}`}>
                        {SEVERITY_ICON[u.severity]}
                        <div>
                            <span className="font-semibold capitalize">{u.type.replace(/_/g, " ")} </span>
                            — {u.message}
                        </div>
                    </div>
                ))}
            </div>

            {/* Hidden risks from risk engine */}
            {hiddenRisks.length > 0 && (
                <div className="pt-3 border-t border-surface-border/50 space-y-2">
                    <div className="flex items-center gap-2">
                        <Zap size={13} className="text-red-400" />
                        <span className="text-xs font-semibold text-red-400 uppercase tracking-wider">Hidden Risk Signals</span>
                    </div>
                    {hiddenRisks.slice(0, 3).map((r, i) => (
                        <p key={i} className="text-xs text-red-300 flex gap-2">
                            <span className="shrink-0">⚠</span> {r}
                        </p>
                    ))}
                </div>
            )}
        </div>
    );
}
