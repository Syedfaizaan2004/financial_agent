"use client";
import { TrendingUp, TrendingDown, Minus, Shield, AlertTriangle, Target } from "lucide-react";
import { outlookColor, outlookLabel, riskColor, fmtMarketCap, fmtPct } from "@/lib/utils";
import type { AgentResponse } from "@/lib/types";

interface SummaryCardsProps {
    data: AgentResponse;
}

export default function SummaryCards({ data }: SummaryCardsProps) {
    const { insights } = data;
    const km = insights.key_metrics;

    const trendIcon =
        insights.forecast_trend === "upward" ? <TrendingUp size={20} className="text-emerald-400" /> :
            insights.forecast_trend === "downward" ? <TrendingDown size={20} className="text-red-400" /> :
                <Minus size={20} className="text-slate-400" />;

    const cards = [
        {
            icon: trendIcon,
            label: "Forecast Trend",
            value: !insights.forecast_trend || insights.forecast_trend === "unavailable" ? "N/A" :
                insights.forecast_trend.charAt(0).toUpperCase() + insights.forecast_trend.slice(1),
            sub: !insights.forecast_trend || insights.forecast_trend === "unavailable" ? "Outside model universe" :
                "Quantitative model signal",
            valueClass: insights.forecast_trend === "upward" ? "text-emerald-400" :
                insights.forecast_trend === "downward" ? "text-red-400" : "text-slate-400",
        },
        {
            icon: <Target size={20} className="text-blue-400" />,
            label: "Overall Outlook",
            value: outlookLabel(insights.outlook || "neutral"),
            sub: `Based on ${data.workflow ?? "quick"} analysis`,
            valueClass: outlookColor(insights.outlook || "neutral"),
        },
        {
            icon: <Shield size={20} className={riskColor(km?.overall_risk)} />,
            label: "Risk Level",
            value: km?.overall_risk
                ? km.overall_risk.charAt(0).toUpperCase() + km.overall_risk.slice(1)
                : "—",
            sub: km?.risk_score != null ? `Risk score: ${km.risk_score.toFixed(1)}` : "Risk score unavailable",
            valueClass: riskColor(km?.overall_risk),
        },
        {
            icon: <AlertTriangle size={20} className="text-amber-400" />,
            label: "Confidence",
            value: `${Math.round(data.confidence * 100)}%`,
            sub: data.contradictions?.length
                ? `${data.contradictions.length} contradiction(s) detected`
                : "No contradictions",
            valueClass: data.confidence >= 0.7 ? "text-emerald-400" :
                data.confidence >= 0.5 ? "text-amber-400" : "text-red-400",
        },
    ];

    // Extra metric: Market Cap if available
    if (km?.market_cap != null) {
        cards.splice(2, 0, {
            icon: <TrendingUp size={20} className="text-purple-400" />,
            label: "Market Cap",
            value: fmtMarketCap(km.market_cap),
            sub: km.pe_ratio != null ? `P/E: ${km.pe_ratio.toFixed(1)}x` : "P/E unavailable",
            valueClass: "text-purple-400",
        });
    }

    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-in">
            {cards.slice(0, 4).map((card, i) => (
                <div key={i} className="card flex flex-col gap-3 hover:border-brand-600/40 transition-colors duration-200">
                    <div className="flex items-center justify-between">
                        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">{card.label}</span>
                        {card.icon}
                    </div>
                    <div>
                        <p className={`text-xl font-bold ${card.valueClass}`}>{card.value}</p>
                        <p className="text-xs text-slate-500 mt-1">{card.sub}</p>
                    </div>
                </div>
            ))}
        </div>
    );
}
