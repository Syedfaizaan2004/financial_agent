// Shared utility helpers

export function cn(...classes: (string | undefined | false | null)[]): string {
    return classes.filter(Boolean).join(" ");
}

export function fmt(value: number | null | undefined, decimals = 1, suffix = ""): string {
    if (value == null) return "—";
    return `${value.toFixed(decimals)}${suffix}`;
}

export function fmtPct(value: number | null | undefined): string {
    if (value == null) return "—";
    return `${value.toFixed(1)}%`;
}

export function fmtMarketCap(value: number | null | undefined): string {
    if (value == null) return "—";
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toFixed(0)}`;
}

export function outlookColor(outlook: string): string {
    switch (outlook) {
        case "positive": return "text-emerald-400";
        case "moderately_positive": return "text-teal-400";
        case "neutral": return "text-amber-400";
        case "cautious": return "text-orange-400";
        case "negative": return "text-red-400";
        default: return "text-slate-400";
    }
}

export function outlookLabel(outlook: string): string {
    return {
        positive: "Positive ↑",
        moderately_positive: "Moderately Positive ↑",
        neutral: "Neutral →",
        cautious: "Cautious ↓",
        negative: "Negative ↓",
    }[outlook] ?? outlook;
}

export function riskColor(level: string | undefined): string {
    switch ((level || "").toLowerCase()) {
        case "low": return "text-emerald-400";
        case "moderate": return "text-amber-400";
        case "high": return "text-red-400";
        case "critical": return "text-red-600";
        default: return "text-slate-400";
    }
}

export function confidenceColor(score: number): string {
    if (score >= 0.70) return "bg-emerald-500";
    if (score >= 0.50) return "bg-amber-500";
    return "bg-red-500";
}

export function confidenceLabel(score: number): string {
    if (score >= 0.80) return "High";
    if (score >= 0.65) return "Moderate-High";
    if (score >= 0.50) return "Moderate";
    if (score >= 0.35) return "Low";
    return "Very Low";
}
