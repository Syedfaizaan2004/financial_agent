"use client";
import { useState, useCallback } from "react";
import type { AgentResponse, AgentRequest } from "@/lib/types";

const API_BASE = "/api";

export function useAgentQuery() {
    const [data, setData] = useState<AgentResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const query = useCallback(async (req: AgentRequest) => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_BASE}/agent`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(req),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail || `HTTP ${res.status}`);
            }
            const json: AgentResponse = await res.json();
            setData(json);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : "Request failed");
        } finally {
            setLoading(false);
        }
    }, []);

    return { data, loading, error, query };
}

export async function runScenario(ticker: string, scenario: string) {
    const res = await fetch(`${API_BASE}/scenario/${encodeURIComponent(ticker)}?scenario=${encodeURIComponent(scenario)}`);
    if (!res.ok) throw new Error(`Scenario API error: ${res.status}`);
    return res.json();
}

export async function savePreferences(prefs: {
    user_id: string;
    risk_profile: string;
    time_horizon: string;
    preferred_metrics: string[];
}) {
    const res = await fetch(`${API_BASE}/memory/preferences`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(prefs),
    });
    if (!res.ok) throw new Error("Could not save preferences");
    return res.json();
}
