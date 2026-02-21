import React from 'react';
import { AgentResponse } from "@/lib/types";
import { Building2, MessageCircle } from "lucide-react";

interface CompanySnapshotProps {
    data: AgentResponse;
}

export function CompanySnapshot({ data }: CompanySnapshotProps) {
    const { company_snapshot, plain_answer } = data;

    if (!company_snapshot && !plain_answer) {
        return null;
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in">
            {/* Company Snapshot Card */}
            {company_snapshot && company_snapshot.length > 0 && (
                <div className="card flex flex-col gap-3">
                    <div className="flex items-center gap-2 border-b border-surface-border pb-3">
                        <Building2 className="w-4 h-4 text-blue-400" />
                        <span className="text-sm font-semibold text-slate-200 uppercase tracking-widest">
                            Building Context
                        </span>
                    </div>
                    <div className="pt-2">
                        <ul className="space-y-3">
                            {company_snapshot.map((point, idx) => (
                                <li key={idx} className="flex gap-3 text-sm text-slate-400 leading-relaxed">
                                    <span className="text-blue-500/70 mt-0.5 flex-shrink-0">•</span>
                                    <span>{point}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>
            )}

            {/* Quick Explanation Card */}
            {plain_answer && (
                <div className="card flex flex-col gap-3">
                    <div className="flex items-center gap-2 border-b border-surface-border pb-3">
                        <MessageCircle className="w-4 h-4 text-emerald-400" />
                        <span className="text-sm font-semibold text-slate-200 uppercase tracking-widest">
                            Quick Explanation
                        </span>
                    </div>
                    <div className="pt-2 flex items-center h-full">
                        <p className="text-sm text-slate-300 leading-relaxed font-medium">
                            {plain_answer}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
