"use client";

import { useState, useEffect } from "react";
import { Play, ChevronRight, ChevronLeft, X, Info, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface DemoStep {
    step: number;
    id: string;
    title: string;
    description: string;
    feature: string;
    query: string;
    hint: string;
    ticker: string;
}

interface DemoGuideProps {
    onRunQuery: (query: string) => void;
    onClose?: () => void;
}

export default function DemoGuide({ onRunQuery, onClose }: DemoGuideProps) {
    const [steps, setSteps] = useState<DemoStep[]>([]);
    const [currentIdx, setCurrentIdx] = useState(0);
    const [expanded, setExpanded] = useState(true);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchSteps() {
            try {
                const res = await fetch("/api/demo/steps");
                if (res.ok) {
                    const data = await res.json();
                    setSteps(data);
                }
            } catch (err) {
                console.error("Failed to fetch demo steps", err);
            } finally {
                setLoading(false);
            }
        }
        fetchSteps();
    }, []);

    if (loading || steps.length === 0) return null;

    const current = steps[currentIdx];

    const handleNext = () => setCurrentIdx(prev => (prev + 1) % steps.length);
    const handlePrev = () => setCurrentIdx(prev => (prev - 1 + steps.length) % steps.length);

    return (
        <div className={cn(
            "fixed bottom-6 right-6 z-50 transition-all duration-300 ease-in-out",
            expanded ? "w-80 shadow-2xl" : "w-12 h-12"
        )}>
            {expanded ? (
                <div className="card bg-surface-card border-brand-500/50 shadow-brand-500/10 p-0 overflow-hidden flex flex-col">
                    {/* Header */}
                    <div className="bg-brand-600 px-4 py-3 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Play size={16} fill="white" />
                            <span className="text-sm font-bold text-white">Guided Demo Mode</span>
                        </div>
                        <button
                            onClick={() => setExpanded(false)}
                            className="text-brand-200 hover:text-white transition-colors"
                        >
                            <X size={16} />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-4 space-y-4">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-[10px] font-bold text-brand-400 uppercase tracking-widest">
                                Step {current.step} / {steps.length}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-border text-slate-400 capitalize">
                                {current.id}
                            </span>
                        </div>

                        <div>
                            <h3 className="text-white font-semibold text-sm mb-1">{current.title}</h3>
                            <p className="text-slate-400 text-xs leading-relaxed">{current.description}</p>
                        </div>

                        <div className="bg-surface/50 rounded-xl p-3 border border-surface-border/50">
                            <div className="flex items-center gap-2 mb-2">
                                <Info size={12} className="text-brand-400" />
                                <span className="text-[10px] font-semibold text-brand-400 uppercase">Pro Tip</span>
                            </div>
                            <p className="text-[11px] text-slate-300 italic">"{current.hint}"</p>
                        </div>

                        <div className="space-y-2 pt-2">
                            <button
                                onClick={() => onRunQuery(current.query)}
                                className="w-full btn-primary flex items-center justify-center gap-2 py-2"
                            >
                                <ExternalLink size={14} />
                                Run Step Query
                            </button>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handlePrev}
                                    className="flex-1 btn-ghost py-2 flex items-center justify-center"
                                >
                                    <ChevronLeft size={16} />
                                </button>
                                <button
                                    onClick={handleNext}
                                    className="flex-1 btn-ghost py-2 flex items-center justify-center"
                                >
                                    <ChevronRight size={16} />
                                </button>
                            </div>
                        </div>
                    </div>

                    <div className="bg-surface/30 px-4 py-2 text-[10px] text-slate-500 text-center border-t border-surface-border/50">
                        Feature: <span className="text-brand-400">{current.feature}</span>
                    </div>
                </div>
            ) : (
                <button
                    onClick={() => setExpanded(true)}
                    className="w-12 h-12 bg-brand-600 hover:bg-brand-500 rounded-full flex items-center justify-center shadow-lg shadow-brand-600/30 text-white transition-all transform hover:scale-110 active:scale-95"
                >
                    <Play size={20} fill="white" />
                </button>
            )}
        </div>
    );
}
