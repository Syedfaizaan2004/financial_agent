// API type definitions for the Financial Research Agent

export interface AgentRequest {
    query: string;
    user_id?: string;
    scenario?: string;
    mode?: "quick" | "deep";
    analysis_type?: string;
}

export interface KeyMetrics {
    net_margin?: number | null;
    roe?: number | null;
    pe_ratio?: number | null;
    market_cap?: number | null;
    overall_risk?: string;
    risk_score?: number;
}

export interface Contradiction {
    type: string;
    severity: "critical" | "warning" | "note";
    signal_a: string;
    signal_b: string;
    message: string;
}

export interface Uncertainty {
    type: string;
    severity: "high" | "medium" | "low";
    field: string;
    message: string;
}

export interface Insights {
    ticker?: string;
    strengths?: string[];
    risks?: string[];
    opportunities?: string[];
    outlook?: "positive" | "moderately_positive" | "neutral" | "cautious" | "negative";
    forecast_trend?: "upward" | "downward" | "neutral" | "unavailable";
    key_metrics?: KeyMetrics;
    scenario_impact?: string;
    peer_positioning?: string;
    confidence?: number;
    contradictions?: Contradiction[];
    uncertainties?: Uncertainty[];
    personalized_notes?: string[];
    bull_case?: string;
    bear_case?: string;
    hidden_risks?: string[];
    suggested_next_steps?: string[];
}

export interface InvestmentMemo {
    ticker?: string;
    executive_summary?: string;
    bull_case?: string | string[];
    bear_case?: string | string[];
    key_strengths?: string[];
    key_risks?: string[];
    outlook?: string;
    confidence?: number;
    analyst_note?: string;
    generated_by?: string;
}

export interface ForecastData {
    supported: boolean;
    message?: string;
    direction?: string;
    prob_up?: number;
    prob_down?: number;
    confidence?: number;
    expected_movement?: number;
}

export interface RiskData {
    ticker?: string;
    overall_risk?: string;
    overall_risk_score?: number;
    leverage_risk?: { risk_level: string; flags: string[] };
    liquidity_risk?: { risk_level: string; flags: string[] };
    earnings_stability?: { classification: string; total_years_analyzed: number };
    hidden_risks?: string[];
    key_risks?: string[];
}

export interface ScenarioData {
    ticker: string;
    scenario: string;
    scenario_label: string;
    scenario_description: string;
    risk_outlook: string;
    summary: string[];
    revenue_stress?: { scenario_adjustment_pp?: number; adjusted_growth?: number | null };
    margin_stress?: { scenario_adjustment_pp?: number; adjusted_margin?: number | null; margin_state?: string };
}

export interface AgentResponse {
    query: string;
    user_id: string;
    ticker: string | null;
    intent: string;
    intent_confidence: string;
    workflow: string;
    confidence: number;
    contradictions: Contradiction[];
    uncertainties: Uncertainty[];
    company_snapshot?: string[];
    plain_answer?: string;
    insights: Insights;
    investment_memo: InvestmentMemo;
    raw_data: {
        forecast?: ForecastData;
        fundamentals?: Record<string, unknown>;
        risk?: RiskData;
        peer_comparison?: any;
        scenario?: ScenarioData;
        memo?: InvestmentMemo;
        risk_data?: RiskData;
    };
    next_analysis: string[];
    agent_errors: string[];
    status: "ok" | "partial" | "failed";
    llm_provider?: string;
    llm_model?: string;
}
