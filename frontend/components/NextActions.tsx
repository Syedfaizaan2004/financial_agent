"use client";
import { ArrowRight, BarChart2, CloudLightning, Search, TrendingUp } from "lucide-react";

const ACTION_ICONS: Record<string, React.ReactNode> = {
    Compare: <BarChart2 size={14} />,
    Run: <CloudLightning size={14} />,
    Analyse: <TrendingUp size={14} />,
    Analyze: <TrendingUp size={14} />,
    Review: <Search size={14} />,
    Examine: <Search size={14} />,
    Deep: <Search size={14} />,
    Get: <TrendingUp size={14} />,
};

function iconForAction(text: string) {
    const first = text.split(" ")[0];
    return ACTION_ICONS[first] ?? <ArrowRight size={14} />;
}

interface NextActionsProps {
    suggestions: string[];
    onAction: (suggestion: string) => void;
}

export default function NextActions({ suggestions, onAction }: NextActionsProps) {
    if (!suggestions || suggestions.length === 0) return null;

    return (
        <div className="card space-y-3 animate-slide-up">
            <div className="flex items-center gap-2">
                <ArrowRight size={15} className="text-brand-500" />
                <h3 className="text-sm font-semibold text-white">Suggested Next Steps</h3>
            </div>

            <div className="space-y-2">
                {suggestions.map((s, i) => (
                    <button
                        key={i}
                        onClick={() => onAction(s)}
                        className="w-full flex items-center gap-3 p-3 rounded-xl border border-surface-border/60
              bg-surface-border/10 hover:bg-brand-900/20 hover:border-brand-600/50
              text-left transition-all duration-200 group active:scale-[0.98]"
                    >
                        <span className="text-brand-500 shrink-0 group-hover:translate-x-0.5 transition-transform">
                            {iconForAction(s)}
                        </span>
                        <span className="text-sm text-slate-300 group-hover:text-white transition-colors">{s}</span>
                        <ArrowRight size={12} className="ml-auto text-slate-600 group-hover:text-brand-500 transition-colors" />
                    </button>
                ))}
            </div>
        </div>
    );
}
