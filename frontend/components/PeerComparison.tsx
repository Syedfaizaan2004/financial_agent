"use client";
import { Users } from "lucide-react";

interface PeerData {
    peer_group?: string[];
    summary?: string[];
    comparison_table?: Record<string, Record<string, number | string | null>>;
}

interface PeerComparisonProps {
    data: PeerData | null | undefined;
    ticker: string;
}

export default function PeerComparison({ data, ticker }: PeerComparisonProps) {
    if (!data || (!data.peer_group?.length && !data.summary?.length)) {
        return (
            <div className="card text-center py-8">
                <Users size={24} className="mx-auto text-slate-600 mb-2" />
                <p className="text-sm text-slate-500">No peer comparison available for {ticker}.</p>
                <p className="text-xs text-slate-600 mt-1">Run a deep-research query to include peer benchmarking.</p>
            </div>
        );
    }

    return (
        <div className="card space-y-4 animate-slide-up">
            <div className="flex items-center gap-2">
                <Users size={15} className="text-purple-400" />
                <h3 className="text-sm font-semibold text-white">Peer Comparison</h3>
                {data.peer_group?.length && (
                    <span className="ml-auto text-xs text-slate-500">vs {data.peer_group.slice(0, 3).join(", ")}</span>
                )}
            </div>

            {/* Peer group pills */}
            {data.peer_group && data.peer_group.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    <span className="px-2.5 py-1 rounded-lg bg-brand-900/40 border border-brand-700/40 text-xs font-bold text-brand-400">
                        {ticker} ◄ Target
                    </span>
                    {data.peer_group.slice(0, 5).map((peer, i) => (
                        <span key={i} className="px-2.5 py-1 rounded-lg bg-surface-border/30 border border-surface-border/50 text-xs text-slate-400">
                            {peer}
                        </span>
                    ))}
                </div>
            )}

            {/* Summary points */}
            {data.summary && data.summary.length > 0 && (
                <ul className="space-y-2">
                    {data.summary.slice(0, 5).map((point, i) => {
                        const isPositive = /better|above|strong|outperform|higher/i.test(point);
                        const isNegative = /weaker|below|under|lag|lower/i.test(point);
                        return (
                            <li key={i} className="flex items-start gap-2 text-xs text-slate-300">
                                <span className={`mt-0.5 font-bold shrink-0 ${isPositive ? "text-emerald-400" : isNegative ? "text-red-400" : "text-slate-400"}`}>
                                    {isPositive ? "↑" : isNegative ? "↓" : "→"}
                                </span>
                                {point}
                            </li>
                        );
                    })}
                </ul>
            )}
        </div>
    );
}
