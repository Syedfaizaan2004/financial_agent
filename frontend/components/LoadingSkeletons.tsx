"use client";

export function SkeletonCard({ lines = 3, className = "" }: { lines?: number; className?: string }) {
    return (
        <div className={`card space-y-3 ${className}`}>
            <div className="skeleton h-4 w-1/3 rounded" />
            {Array.from({ length: lines }).map((_, i) => (
                <div key={i} className="skeleton h-3 rounded" style={{ width: `${80 - i * 12}%` }} />
            ))}
        </div>
    );
}

export function SkeletonChartCard() {
    return (
        <div className="card space-y-3">
            <div className="skeleton h-4 w-1/4 rounded" />
            <div className="skeleton h-48 w-full rounded-xl" />
        </div>
    );
}

export function SkeletonSummaryCards() {
    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="card space-y-2">
                    <div className="skeleton h-3 w-1/2 rounded" />
                    <div className="skeleton h-6 w-2/3 rounded" />
                    <div className="skeleton h-3 w-3/4 rounded" />
                </div>
            ))}
        </div>
    );
}

export function AnalyzingSpinner({ text = "Analyzing…" }: { text?: string }) {
    return (
        <div className="flex items-center gap-3 text-sm text-blue-400">
            <div className="w-4 h-4 rounded-full border-2 border-blue-400 border-t-transparent animate-spin" />
            <span className="animate-pulse">{text}</span>
        </div>
    );
}
