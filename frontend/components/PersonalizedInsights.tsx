"use client";
import { User } from "lucide-react";

interface PersonalizedInsightsProps {
    notes: string[];
    riskProfile?: string;
    timeHorizon?: string;
}

export default function PersonalizedInsights({
    notes,
    riskProfile,
    timeHorizon,
}: PersonalizedInsightsProps) {
    if (!notes || notes.length === 0) return null;

    const profileColor = riskProfile === "conservative" ? "text-blue-400"
        : riskProfile === "aggressive" ? "text-red-400"
            : "text-emerald-400";

    return (
        <div className="card border-brand-600/30 bg-brand-900/10 space-y-3 animate-slide-up">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <User size={15} className="text-brand-500" />
                    <h3 className="text-sm font-semibold text-white">Personalized Insights</h3>
                </div>
                <div className="flex gap-2">
                    {riskProfile && (
                        <span className={`badge-blue text-xs capitalize ${profileColor}`}>
                            {riskProfile}
                        </span>
                    )}
                    {timeHorizon && (
                        <span className="badge-blue text-xs capitalize">{timeHorizon}-term</span>
                    )}
                </div>
            </div>

            <ul className="space-y-2.5">
                {notes.map((note, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-sm text-slate-300">
                        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-brand-500 shrink-0" />
                        {note}
                    </li>
                ))}
            </ul>
        </div>
    );
}
