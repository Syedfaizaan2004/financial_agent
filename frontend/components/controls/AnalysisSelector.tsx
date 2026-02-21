import { useState } from "react";
import { ChevronDown, Filter } from "lucide-react";

export type AnalysisType =
    | "overview"
    | "compare"
    | "bullbear"
    | "risk"
    | "hidden_risks"
    | "scenario"
    | "next_analysis";

interface AnalysisSelectorProps {
    selectedType: AnalysisType;
    onChange: (type: AnalysisType) => void;
}

const ANALYSIS_OPTIONS: Record<AnalysisType, { label: string; desc: string }> = {
    overview: { label: "Overview", desc: "General summary and fundamental analysis" },
    compare: { label: "Compare Companies", desc: "Peer comparison and relative valuation" },
    bullbear: { label: "Bull vs Bear Thesis", desc: "Detailed arguments for and against" },
    risk: { label: "Risk Analysis", desc: "Key risk signals and qualitative risks" },
    hidden_risks: { label: "Hidden Risks", desc: "Overlooked and nuanced tail risks" },
    scenario: { label: "Scenario Stress Test", desc: "Macroeconomic scenario simulation" },
    next_analysis: { label: "Next Analysis", desc: "Personalized suggestions for what's next" },
};

export default function AnalysisSelector({ selectedType, onChange }: AnalysisSelectorProps) {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="relative inline-block text-left z-20">
            <div>
                <button
                    type="button"
                    onClick={() => setIsOpen(!isOpen)}
                    className="inline-flex w-48 justify-between gap-1 rounded-md bg-zinc-900/80 px-4 py-2 text-sm font-semibold text-zinc-100 shadow-sm ring-1 ring-inset ring-zinc-700 hover:bg-zinc-800 transition-colors duration-200 items-center"
                    id="analysis-selector-button"
                    aria-expanded={isOpen}
                    aria-haspopup="true"
                >
                    <div className="flex items-center gap-2 overflow-hidden">
                        <Filter className="h-4 w-4 text-zinc-400 shrink-0" />
                        <span className="truncate">{ANALYSIS_OPTIONS[selectedType].label}</span>
                    </div>
                    <ChevronDown className="-mr-1 h-5 w-5 text-zinc-400 shrink-0" aria-hidden="true" />
                </button>
            </div>

            {isOpen && (
                <div
                    className="absolute right-0 z-20 mt-2 w-64 origin-top-right rounded-md bg-zinc-900 shadow-xl ring-1 ring-white/10 ring-opacity-5 focus:outline-none overflow-hidden"
                    role="menu"
                    aria-orientation="vertical"
                    aria-labelledby="analysis-selector-button"
                    tabIndex={-1}
                >
                    <div className="py-1 max-h-80 overflow-y-auto custom-scrollbar" role="none">
                        {Object.entries(ANALYSIS_OPTIONS).map(([key, config]) => {
                            const typeKey = key as AnalysisType;
                            const isSelected = selectedType === typeKey;

                            return (
                                <button
                                    key={typeKey}
                                    onClick={() => {
                                        onChange(typeKey);
                                        setIsOpen(false);
                                    }}
                                    className={`${isSelected ? "bg-zinc-800 text-white" : "text-zinc-300"
                                        } group flex w-full items-center px-4 py-3 text-sm hover:bg-zinc-800 hover:text-white transition-colors duration-200 border-b border-zinc-800/50 last:border-0`}
                                    role="menuitem"
                                    tabIndex={-1}
                                >
                                    <div className="flex flex-col text-left w-full">
                                        <span className={`font-medium ${isSelected ? "text-cyan-400" : "text-zinc-200"}`}>
                                            {config.label}
                                        </span>
                                        <span className="text-xs text-zinc-500 mt-1 line-clamp-1">{config.desc}</span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
