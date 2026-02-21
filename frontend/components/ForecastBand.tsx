"use client";
import {
    AreaChart, Area, XAxis, YAxis, Tooltip, ReferenceLine,
    ResponsiveContainer, CartesianGrid
} from "recharts";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { ForecastData } from "@/lib/types";

interface ForecastBandProps {
    forecast: ForecastData | undefined;
    ticker: string;
}

// Build synthetic chart data representing historical + forecast band
function buildChartData(forecast: ForecastData) {
    const horizon = 10;
    const base = 100;
    const probUp = forecast.prob_up ?? 0.5;
    const probDown = forecast.prob_down ?? 0.5;
    const expected = (forecast.expected_movement ?? 0);

    const points = [];
    // Historical (past 10 periods)
    for (let i = -10; i <= 0; i++) {
        points.push({
            period: i,
            label: i === 0 ? "Now" : `T${i}`,
            price: base + i * 0.5 + (Math.sin(i * 0.8) * 3),
            upper: null,
            lower: null,
            isForecast: false,
        });
    }
    // Forecast band (future periods)
    for (let i = 1; i <= horizon; i++) {
        const mid = base + expected * (i / horizon) * 10;
        const band = 3 + i * (1 - (forecast.confidence ?? 0.5)) * 1.5;
        points.push({
            period: i,
            label: `T+${i}`,
            price: mid,
            upper: mid + band,
            lower: mid - band,
            isForecast: true,
        });
    }
    return points;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-surface-card border border-surface-border rounded-xl px-3 py-2 text-xs shadow-xl">
            <p className="text-slate-400 mb-1">{label}</p>
            {payload.map((p: { name: string; value: number | null; color: string }, i: number) => (
                p.value != null && (
                    <p key={i} style={{ color: p.color }} className="font-medium">
                        {p.name}: {p.value.toFixed(1)}
                    </p>
                )
            ))}
        </div>
    );
};

export default function ForecastBand({ forecast, ticker }: ForecastBandProps) {
    if (!forecast || !forecast.supported) {
        return (
            <div className="card flex flex-col items-center justify-center py-10 text-center">
                <p className="text-slate-400 text-sm">Forecast not available for <strong className="text-white">{ticker}</strong>.</p>
                <p className="text-xs text-slate-500 mt-1">This ticker is outside the model&apos;s training universe.</p>
            </div>
        );
    }

    // Normalize field names — backend uses 'trend' and nests prob_up inside xgb_output
    const rawDirection = forecast.direction ?? (forecast as any).trend ?? "neutral";
    const direction = rawDirection === "upward" ? "up" : rawDirection === "downward" ? "down" : rawDirection;
    const probUp = forecast.prob_up ?? (forecast as any).xgb_output?.prob_up ?? 0.5;
    const probDown = forecast.prob_down ?? (forecast as any).xgb_output?.prob_down ?? 0.5;
    const adjustedForecast = { ...forecast, direction, prob_up: probUp, prob_down: probDown };

    const data = buildChartData(adjustedForecast);
    const probPct = Math.round(probUp * 100);
    const confPct = Math.round((forecast.confidence ?? 0.5) * 100);
    const modelsUsed: string[] = (forecast as any).models_used ?? [];
    const modelAgreement: boolean = (forecast as any).model_agreement ?? false;

    return (
        <div className="card space-y-4 animate-slide-up">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    {direction === "up"
                        ? <TrendingUp size={16} className="text-emerald-400" />
                        : <TrendingDown size={16} className="text-red-400" />}
                    <h3 className="text-sm font-semibold text-white">Price Direction Forecast</h3>
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                    <span className={`badge-${direction === "up" ? "green" : "red"}`}>
                        {direction === "up" ? "↑ Upward" : "↓ Downward"} {probPct}%
                    </span>
                    <span className="badge-blue">Conf {confPct}%</span>
                    {modelsUsed.length > 0 && (
                        <span className={`badge-${modelAgreement ? "green" : "yellow"}`}>
                            {modelsUsed.join(" + ")} {modelAgreement ? "✓ Agree" : "≠ Split"}
                        </span>
                    )}
                </div>
            </div>

            {/* Chart */}
            <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="gradUp" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                            </linearGradient>
                            <linearGradient id="gradBand" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.03} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" strokeOpacity={0.5} />
                        <XAxis dataKey="label" tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: "#64748b", fontSize: 10 }} axisLine={false} tickLine={false} />
                        <Tooltip content={<CustomTooltip />} />
                        <ReferenceLine x="Now" stroke="#94a3b8" strokeDasharray="4 2" label={{ value: "Today", fill: "#94a3b8", fontSize: 10 }} />
                        {/* Historical price */}
                        <Area dataKey="price" name="Price"
                            stroke="#10b981" strokeWidth={2} fill="url(#gradUp)"
                            dot={false} connectNulls />
                        {/* Uncertainty band — upper */}
                        <Area dataKey="upper" name="Upper Band"
                            stroke="#3b82f6" strokeWidth={1} strokeDasharray="4 2"
                            fill="url(#gradBand)" dot={false} connectNulls />
                        {/* Uncertainty band — lower */}
                        <Area dataKey="lower" name="Lower Band"
                            stroke="#3b82f6" strokeWidth={1} strokeDasharray="4 2"
                            fill="transparent" dot={false} connectNulls />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <p className="text-xs text-slate-500 text-center">
                Shaded band = uncertainty range. Wider = lower model confidence.
            </p>
        </div>
    );
}
