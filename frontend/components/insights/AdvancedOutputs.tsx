import { BadgeAlert, Scale, ArrowRightCircle } from "lucide-react";
import type { Insights } from "@/lib/types";

interface AdvancedOutputsProps {
    insights: Insights;
    onNextAction: (action: string) => void;
}

export default function AdvancedOutputs({ insights, onNextAction }: AdvancedOutputsProps) {
    if (!insights.bull_case && !insights.bear_case && !insights.hidden_risks && (!insights.suggested_next_steps || insights.suggested_next_steps.length === 0)) {
        return null;
    }

    return (
        <div className="space-y-4 animate-fade-in w-full">
            {/* Bull vs Bear Thesis */}
            {(insights.bull_case || insights.bear_case) && (
                <div className="card bg-surface-card border-surface-border">
                    <div className="flex items-center gap-2 mb-4 pb-2 border-b border-surface-border/50">
                        <Scale size={18} className="text-purple-400" />
                        <h3 className="font-semibold text-white">Bull vs Bear Thesis</h3>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        {insights.bull_case && (
                            <div className="bg-emerald-950/20 rounded-lg p-4 border border-emerald-900/30">
                                <h4 className="text-emerald-400 font-semibold mb-2 flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-emerald-500" />
                                    Bull Case
                                </h4>
                                <div className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">
                                    {insights.bull_case}
                                </div>
                            </div>
                        )}

                        {insights.bear_case && (
                            <div className="bg-red-950/20 rounded-lg p-4 border border-red-900/30">
                                <h4 className="text-red-400 font-semibold mb-2 flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-red-500" />
                                    Bear Case
                                </h4>
                                <div className="text-sm text-slate-300 whitespace-pre-line leading-relaxed">
                                    {insights.bear_case}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Hidden / Overlooked Risks */}
            {insights.hidden_risks && insights.hidden_risks.length > 0 && (
                <div className="card bg-orange-950/20 border-orange-900/30">
                    <div className="flex items-center gap-2 mb-4">
                        <BadgeAlert size={18} className="text-orange-400" />
                        <h3 className="font-semibold text-orange-400">Overlooked & Hidden Risks</h3>
                    </div>
                    <ul className="space-y-3">
                        {insights.hidden_risks.map((risk, idx) => (
                            <li key={idx} className="flex gap-3 text-sm text-slate-300 bg-surface/40 p-3 rounded-md border border-surface-border/50">
                                <span className="mt-0.5 text-orange-500 font-bold">{idx + 1}.</span>
                                <span>{risk}</span>
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Suggested Next Steps given by NextAnalysis Workflow */}
            {insights.suggested_next_steps && insights.suggested_next_steps.length > 0 && (
                <div className="card bg-blue-950/20 border-blue-900/30">
                    <div className="flex items-center gap-2 mb-4">
                        <ArrowRightCircle size={18} className="text-blue-400" />
                        <h3 className="font-semibold text-blue-400">Suggested Next Steps</h3>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {insights.suggested_next_steps.map((step, idx) => (
                            <button
                                key={idx}
                                onClick={() => onNextAction(step)}
                                className="text-left text-sm bg-blue-900/30 hover:bg-blue-800/50 text-blue-200 px-4 py-2 rounded-md border border-blue-700/50 transition-colors"
                            >
                                {step}
                            </button>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
