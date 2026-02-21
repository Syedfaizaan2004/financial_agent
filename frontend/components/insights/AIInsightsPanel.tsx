"use client";
import { CheckCircle, AlertCircle, Zap, TrendingUp } from "lucide-react";
import { outlookColor, outlookLabel } from "@/lib/utils";
import type { Insights } from "@/lib/types";

interface AIInsightsPanelProps {
    insights: Insights;
}

const OUTLOOK_BG: Record<string, string> = {
    positive: "from-emerald-950/60 to-surface-card border-emerald-800/50",
    moderately_positive: "from-teal-950/60 to-surface-card border-teal-800/50",
    neutral: "from-amber-950/40 to-surface-card border-amber-800/40",
    cautious: "from-orange-950/40 to-surface-card border-orange-800/40",
    negative: "from-red-950/60 to-surface-card border-red-900/50",
};

export default function AIInsightsPanel({ insights }: AIInsightsPanelProps) {
    const bgClass = insights.outlook && OUTLOOK_BG[insights.outlook] ? OUTLOOK_BG[insights.outlook] : "from-surface-card to-surface-card border-surface-border";

    return (
        <div className={`card bg-gradient-to-br ${bgClass} animate-slide-up`}>
            {/* Header */}
            <div className="flex items-start justify-between mb-5">
                <div>
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">AI Research Insights</p>
                    <h2 className="text-2xl font-bold text-white">{insights.ticker}</h2>
                </div>
                <span className={`text-lg font-bold ${insights.outlook ? outlookColor(insights.outlook) : 'text-slate-400'}`}>
                    {insights.outlook ? outlookLabel(insights.outlook) : 'Pending Analysis'}
                </span>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
                {/* Strengths */}
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <CheckCircle size={14} className="text-emerald-400" />
                        <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Strengths</span>
                    </div>
                    {!insights.strengths || insights.strengths.length === 0 ? (
                        <p className="text-sm text-slate-500 italic">No notable strengths identified.</p>
                    ) : (
                        <ul className="space-y-2">
                            {insights.strengths.slice(0, 4).map((s, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                                    {s}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {/* Risks */}
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <AlertCircle size={14} className="text-red-400" />
                        <span className="text-xs font-semibold text-red-400 uppercase tracking-wider">Risks</span>
                    </div>
                    {!insights.risks || insights.risks.length === 0 ? (
                        <p className="text-sm text-slate-500 italic">No significant risks flagged.</p>
                    ) : (
                        <ul className="space-y-2">
                            {insights.risks.slice(0, 4).map((r, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
                                    {r}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                {/* Opportunities */}
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <TrendingUp size={14} className="text-blue-400" />
                        <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Opportunities</span>
                    </div>
                    {!insights.opportunities || insights.opportunities.length === 0 ? (
                        <p className="text-sm text-slate-500 italic">No opportunities identified.</p>
                    ) : (
                        <ul className="space-y-2">
                            {insights.opportunities.slice(0, 3).map((o, i) => (
                                <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                                    {o}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            </div>

            {/* Scenario impact */}
            {insights.scenario_impact && (
                <div className="mt-4 pt-4 border-t border-surface-border/50 flex items-start gap-2">
                    <Zap size={14} className="text-amber-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-amber-300">{insights.scenario_impact}</p>
                </div>
            )}
        </div>
    );
}
