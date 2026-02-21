"use client";
import { useState } from "react";
import { CloudLightning, TrendingDown, ArrowUp, Activity } from "lucide-react";

export type Scenario = "recession" | "high_inflation" | "rate_hike" | "growth_slowdown";

interface ScenarioOption {
    key: Scenario;
    label: string;
    description: string;
    icon: React.ReactNode;
    color: string;
    border: string;
}

const SCENARIOS: ScenarioOption[] = [
    {
        key: "recession",
        label: "Recession",
        description: "Deep GDP contraction, rising unemployment",
        icon: <TrendingDown size={18} />,
        color: "text-red-400",
        border: "border-red-800/60 bg-red-950/30 hover:border-red-600",
    },
    {
        key: "high_inflation",
        label: "High Inflation",
        description: "CPI surge, margin compression pressure",
        icon: <ArrowUp size={18} />,
        color: "text-orange-400",
        border: "border-orange-800/60 bg-orange-950/30 hover:border-orange-600",
    },
    {
        key: "rate_hike",
        label: "Rate Hike",
        description: "Aggressive central bank tightening cycle",
        icon: <CloudLightning size={18} />,
        color: "text-amber-400",
        border: "border-amber-800/60 bg-amber-950/30 hover:border-amber-600",
    },
    {
        key: "growth_slowdown",
        label: "Growth Slowdown",
        description: "Below-trend growth, demand softening",
        icon: <Activity size={18} />,
        color: "text-blue-400",
        border: "border-blue-800/60 bg-blue-950/30 hover:border-blue-600",
    },
];

interface ScenarioSelectorProps {
    selected?: Scenario | null;
    onSelect: (scenario: Scenario) => void;
    loading?: boolean;
    result?: { risk_outlook?: string; summary?: string[] } | null;
}

export default function ScenarioSelector({
    selected,
    onSelect,
    loading = false,
    result,
}: ScenarioSelectorProps) {
    return (
        <div className="card space-y-4 animate-slide-up">
            <div className="flex items-center gap-2">
                <CloudLightning size={16} className="text-amber-400" />
                <h3 className="text-sm font-semibold text-white">Scenario Stress Testing</h3>
            </div>

            <div className="grid grid-cols-2 gap-2">
                {SCENARIOS.map((s) => {
                    const isActive = selected === s.key;
                    return (
                        <button
                            key={s.key}
                            onClick={() => onSelect(s.key)}
                            disabled={loading}
                            className={`flex items-start gap-2.5 p-3 rounded-xl border transition-all duration-200
                text-left group active:scale-95 disabled:opacity-50
                ${isActive ? s.border + " ring-1 ring-inset ring-white/10" : s.border}
              `}
                        >
                            <span className={`mt-0.5 ${s.color}`}>{s.icon}</span>
                            <div>
                                <p className={`text-xs font-semibold ${s.color}`}>{s.label}</p>
                                <p className="text-xs text-slate-500 mt-0.5 leading-tight">{s.description}</p>
                            </div>
                        </button>
                    );
                })}
            </div>

            {/* Loading state */}
            {loading && (
                <div className="flex items-center gap-2 text-xs text-blue-400 animate-pulse">
                    <div className="w-3 h-3 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
                    Running scenario simulation…
                </div>
            )}

            {/* Scenario result */}
            {result && !loading && (
                <div className="pt-3 border-t border-surface-border/50 space-y-2">
                    {result.risk_outlook && (
                        <p className="text-xs text-amber-300 font-medium">
                            Risk Outlook: <span className="capitalize">{result.risk_outlook}</span>
                        </p>
                    )}
                    {result.summary?.slice(0, 3).map((line: string, i: number) => (
                        <p key={i} className="text-xs text-slate-400 flex gap-2">
                            <span className="text-slate-500 shrink-0">▸</span> {line}
                        </p>
                    ))}
                </div>
            )}
        </div>
    );
}
