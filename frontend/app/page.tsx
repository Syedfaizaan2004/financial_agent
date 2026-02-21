"use client";

import { useState, useCallback, useEffect } from "react";
import { Search, BrainCircuit, RefreshCw, Cpu } from "lucide-react";
import { useAgentQuery, runScenario } from "@/lib/api";
import type { Scenario } from "@/components/ScenarioSelector";
import { cn } from "@/lib/utils";

// Components
import DemoGuide from "@/components/DemoGuide";
import SummaryCards from "@/components/SummaryCards";
import AIInsightsPanel from "@/components/insights/AIInsightsPanel";
import ConfidenceIndicator from "@/components/ConfidenceIndicator";
import RiskAlerts from "@/components/RiskAlerts";
import ForecastBand from "@/components/ForecastBand";
import ScenarioSelector from "@/components/ScenarioSelector";
import PersonalizedInsights from "@/components/PersonalizedInsights";
import NextActions from "@/components/NextActions";
import PeerComparison from "@/components/PeerComparison";
import PreferencesPanel from "@/components/PreferencesPanel";
import ModeSelector, { ModeType } from "@/components/controls/ModeSelector";
import AnalysisSelector, { AnalysisType } from "@/components/controls/AnalysisSelector";
import AdvancedOutputs from "@/components/insights/AdvancedOutputs";
import { CompanySnapshot } from "@/components/insights/CompanySnapshot";
import {
    SkeletonSummaryCards, SkeletonCard, SkeletonChartCard, AnalyzingSpinner,
} from "@/components/LoadingSkeletons";

interface UserPrefs {
    userId: string;
    riskProfile: string;
    timeHorizon: string;
    preferredMetrics: string[];
}

const INITIAL_PREFS: UserPrefs = {
    userId: "default",
    riskProfile: "moderate",
    timeHorizon: "medium",
    preferredMetrics: [],
};

const QUICK_SEARCHES = [
    "Quick summary of Apple",
    "Deep analysis of TSLA with risks",
    "What happens to MSFT in a recession?",
    "Compare GOOGL with peers",
];

export default function DashboardPage() {
    const [queryInput, setQueryInput] = useState("");
    const [prefs, setPrefs] = useState<UserPrefs>(INITIAL_PREFS);
    const [mode, setMode] = useState<ModeType>("quick");
    const [analysisType, setAnalysisType] = useState<AnalysisType>("overview");
    const [scenario, setScenario] = useState<Scenario | null>(null);
    const [scenarioLoading, setScenarioLoading] = useState(false);
    const [scenarioResult, setScenarioResult] = useState<{
        risk_outlook?: string; summary?: string[]
    } | null>(null);
    const [performance, setPerformance] = useState<{ total_ms: number; source: string } | null>(null);

    const { data, loading, error, query } = useAgentQuery();

    const handleSubmit = useCallback(async (q?: string) => {
        const finalQuery = (q ?? queryInput).trim();
        if (!finalQuery) return;
        setScenario(null);
        setScenarioResult(null);
        setPerformance(null);

        // Only send analysis_type if it is explicitly NOT overview
        const payloadType = analysisType === "overview" ? undefined : analysisType;

        await query({
            query: finalQuery,
            user_id: prefs.userId,
            mode: mode,
            analysis_type: payloadType
        });
    }, [queryInput, prefs.userId, mode, analysisType, query]);

    // Update performance state when data arrives
    useEffect(() => {
        if (data && (data as any)._performance) {
            setPerformance((data as any)._performance);
        }
    }, [data]);

    const handleScenario = useCallback(async (s: Scenario) => {
        if (!data?.ticker) return;
        setScenario(s);
        setScenarioLoading(true);
        setScenarioResult(null);
        try {
            const res = await runScenario(data.ticker, s);
            setScenarioResult({
                risk_outlook: res.risk_outlook ?? res.data?.risk_outlook,
                summary: res.summary ?? res.data?.summary ?? [],
            });
        } catch {
            setScenarioResult({ summary: ["Scenario simulation failed — try again."] });
        } finally {
            setScenarioLoading(false);
        }
    }, [data?.ticker]);

    const handleNextAction = useCallback((suggestion: string) => {
        // Translate suggestions into queries
        const ticker = data?.ticker ?? "";
        let q = suggestion;
        if (/recession/i.test(suggestion)) handleScenario("recession");
        else if (/inflation/i.test(suggestion)) handleScenario("high_inflation");
        else if (/rate hike/i.test(suggestion)) handleScenario("rate_hike");
        else if (/compare|peer/i.test(suggestion)) {
            q = `Compare ${ticker} against competitors`;
            setQueryInput(q);
            setAnalysisType("compare");
            handleSubmit(q);
        } else if (/deep.research|comprehensive/i.test(suggestion)) {
            q = `Deep analysis of ${ticker} including risks and peers`;
            setQueryInput(q);
            setMode("deep");
            setAnalysisType("overview");
            handleSubmit(q);
        } else if (/forecast/i.test(suggestion)) {
            q = `Forecast for ${ticker}`;
            setQueryInput(q);
            setAnalysisType("overview");
            handleSubmit(q);
        } else {
            q = `${suggestion} for ${ticker}`;
            setQueryInput(q);
            setAnalysisType("overview");
            handleSubmit(q);
        }
    }, [data?.ticker, handleScenario, handleSubmit]);

    const insights = data?.insights;
    const riskData = data?.raw_data?.risk;
    const peerData = data?.raw_data?.peer_comparison;
    const forecastData = data?.raw_data?.forecast;

    return (
        <div className="min-h-screen bg-surface">
            {/* ── TOP NAVIGATION ── */}
            <nav className="border-b border-surface-border bg-surface/80 backdrop-blur-sm sticky top-0 z-40">
                <div className="max-w-7xl mx-auto px-4 py-3 flex flex-col gap-3">
                    <div className="flex items-center gap-4 w-full">
                        <div className="flex items-center gap-2.5">
                            <BrainCircuit size={20} className="text-brand-500" />
                            <span className="font-bold text-white text-sm tracking-tight hidden sm:block">
                                Financial Agent
                            </span>
                        </div>

                        {/* Search bar */}
                        <form
                            className="flex-1 flex items-center gap-2 bg-surface-card border border-surface-border
                  rounded-xl px-3 py-2 flex-wrap sm:flex-nowrap"
                            onSubmit={e => { e.preventDefault(); handleSubmit(); }}
                        >
                            <Search size={14} className="text-slate-500 shrink-0 hidden sm:block" />
                            <input
                                value={queryInput}
                                onChange={e => setQueryInput(e.target.value)}
                                placeholder="Ask any financial question… e.g. Compare AAPL & MSFT"
                                className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 outline-none w-full min-w-[200px]"
                            />

                            <div className="flex items-center gap-2 mt-2 sm:mt-0 ml-auto flex-wrap sm:flex-nowrap">
                                <ModeSelector selectedMode={mode} onChange={setMode} />
                                <AnalysisSelector selectedType={analysisType} onChange={setAnalysisType} />

                                <button
                                    type="submit"
                                    disabled={loading || !queryInput.trim()}
                                    className="btn-primary text-xs px-4 py-2 flex items-center gap-2 h-9"
                                >
                                    {loading ? <AnalyzingSpinner text="" /> : "Analyze"}
                                </button>
                            </div>
                        </form>

                        <div className="hidden md:block">
                            <PreferencesPanel prefs={prefs} onChange={setPrefs} />
                        </div>
                    </div>
                </div>
            </nav>

            <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
                {/* ── EMPTY STATE ── */}
                {!data && !loading && !error && (
                    <div className="text-center py-20 animate-fade-in">
                        <BrainCircuit size={48} className="mx-auto text-brand-500/40 mb-5" />
                        <h1 className="text-2xl font-bold text-white mb-2">AI Financial Research Agent</h1>
                        <p className="text-slate-400 text-sm mb-8 max-w-md mx-auto">
                            Ask any question about stocks, risks, forecasts, and more.
                            The AI agent will research, analyse, and synthesize insights for you.
                        </p>
                        <div className="flex flex-wrap gap-2 justify-center">
                            {QUICK_SEARCHES.map((qs, i) => (
                                <button
                                    key={i}
                                    onClick={() => { setQueryInput(qs); handleSubmit(qs); }}
                                    className="btn-ghost text-xs"
                                >
                                    {qs}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* ── ERROR STATE ── */}
                {error && !loading && (
                    <div className="card border-red-800/50 bg-red-950/20 flex items-center justify-between">
                        <p className="text-red-400 text-sm">{error}</p>
                        <button onClick={() => handleSubmit()} className="btn-ghost text-xs flex items-center gap-1">
                            <RefreshCw size={12} /> Retry
                        </button>
                    </div>
                )}

                {/* ── LOADING SKELETONS ── */}
                {loading && (
                    <div className="space-y-6 animate-pulse-once">
                        <div className="flex items-center gap-3">
                            <AnalyzingSpinner text="Running AI research pipeline…" />
                        </div>
                        <SkeletonSummaryCards />
                        <SkeletonCard lines={4} />
                        <div className="grid lg:grid-cols-3 gap-4">
                            <SkeletonCard lines={5} />
                            <SkeletonCard lines={3} />
                            <SkeletonChartCard />
                        </div>
                    </div>
                )}

                {/* ── RESULTS ── */}
                {data && !loading && insights && (
                    <div className="space-y-6 animate-fade-in">
                        {/* Performance & Model Indicator */}
                        <div className="flex items-center justify-between -mb-4 mt-2">
                            {/* LLM Source */}
                            <div>
                                {data.llm_provider && (
                                    <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-medium bg-slate-900/40 px-2 py-1 rounded-md border border-slate-800/50">
                                        <Cpu size={12} className="opacity-70 text-indigo-400" />
                                        Powered by: <span className="text-slate-300">
                                            {data.llm_provider === "disabled"
                                                ? "Offline Rule-Engine"
                                                : (data.llm_model !== "none" ? `${data.llm_model?.toUpperCase()} (${data.llm_provider.toUpperCase()})` : data.llm_provider.toUpperCase())}
                                        </span>
                                    </div>
                                )}
                            </div>

                            {/* Performance */}
                            {performance && (
                                <div className="flex items-center gap-2">
                                    <span className={cn(
                                        "text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded",
                                        performance.source === "cache" ? "bg-emerald-950/50 text-emerald-400 border border-emerald-800/30" : "bg-blue-950/50 text-blue-400 border border-blue-800/30"
                                    )}>
                                        {performance.source}
                                    </span>
                                    <span className="text-[10px] text-slate-500 font-medium">
                                        Response: {performance.total_ms}ms
                                    </span>
                                </div>
                            )}
                        </div>

                        {/* 1. Summary Cards */}
                        <SummaryCards data={data} />

                        {/* 1.5 Company Snapshot */}
                        <CompanySnapshot data={data} />

                        {/* 2. AI Insights Panel (full width) */}
                        <AIInsightsPanel insights={insights} />

                        {/* 3. 3-column grid: Risk + Confidence + Forecast */}
                        <div className="grid lg:grid-cols-3 gap-4">
                            <div className="space-y-4">
                                <RiskAlerts uncertainties={data.uncertainties} riskData={riskData} />
                                <PersonalizedInsights
                                    notes={insights.personalized_notes ?? []}
                                    riskProfile={prefs.riskProfile}
                                    timeHorizon={prefs.timeHorizon}
                                />
                            </div>
                            <div>
                                <ConfidenceIndicator
                                    score={data.confidence}
                                    contradictions={data.contradictions}
                                    uncertainties={data.uncertainties}
                                />
                            </div>
                            <div>
                                <ForecastBand forecast={forecastData} ticker={data.ticker || ""} />
                            </div>
                        </div>

                        {/* 4. Scenario + Peer side-by-side */}
                        <div className="grid lg:grid-cols-2 gap-4">
                            <ScenarioSelector
                                selected={scenario}
                                onSelect={handleScenario}
                                loading={scenarioLoading}
                                result={scenarioResult}
                            />
                            {data.ticker && <PeerComparison data={peerData} ticker={data.ticker} />}
                        </div>

                        {/* 4.5 Advanced Outputs (Bull/Bear, Hidden Risks) */}
                        <div className="w-full">
                            <AdvancedOutputs
                                insights={insights}
                                onNextAction={handleNextAction}
                            />
                        </div>

                        {/* 5. Next Actions (full width) */}
                        <NextActions
                            suggestions={data.next_analysis}
                            onAction={handleNextAction}
                        />

                        {/* 6. Footer metadata */}
                        <div className="flex items-center justify-between text-xs text-slate-600 border-t border-surface-border pt-4">
                            <span>Query: <span className="text-slate-500">{data.query}</span></span>
                            <span>Workflow: <span className="text-slate-500">{data.workflow}</span></span>
                            <span>Status: <span className={data.status === "ok" ? "text-emerald-600" : "text-amber-600"}>{data.status}</span></span>
                        </div>
                    </div>
                )}
            </main>

            {/* Guided Demo Widget */}
            <DemoGuide onRunQuery={(q) => handleSubmit(q || "")} />
        </div>
    );
}
