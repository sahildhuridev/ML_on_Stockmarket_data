import React, { useState, useEffect } from "react";
import api from "../api/axios";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    Legend,
} from "recharts";
import {
    Play,
    Loader2,
    AlertCircle,
    Trophy,
    TrendingUp,
    TrendingDown,
    Activity,
    Cpu,
    BarChart3,
    Clock,
    CheckCircle2,
    XCircle,
    Layers,
    FlaskConical,
    History,
    ChevronDown,
    ChevronRight,
    Zap,
    Crown,
    Timer,
    Medal,
    Eye,
    Target,
    ShieldAlert,
    ShieldCheck,
    LineChart as LineChartIcon
} from "lucide-react";

import {
    LineChart,
    Line,
} from "recharts";

/* ── colour helpers ─────────────────────────────────────────── */
const MODEL_COLORS = {
    LinearRegression: "#2962FF",
    ARIMA: "#089981",
    LSTM: "#f7931a",
};

const pctChange = (curr, pred) => {
    if (!curr || curr === 0) return 0;
    return ((pred - curr) / curr) * 100;
};

/* ── sub-components ─────────────────────────────────────────── */

const MetricPill = ({ label, value, unit = "", color = "#d1d4dc" }) => (
    <div className="bg-[#131722] rounded-lg px-3 py-2 text-center border border-[#2b2b43]/50">
        <div className="text-[10px] text-[#787b86] uppercase tracking-wider mb-0.5">
            {label}
        </div>
        <div className="text-sm font-mono font-semibold" style={{ color }}>
            {typeof value === "number" ? value.toFixed(4) : value}
            {unit}
        </div>
    </div>
);

const PipelineStageBadge = ({ stage, idx }) => {
    const icons = [Layers, CheckCircle2, Zap, Cpu, BarChart3, FlaskConical, TrendingUp];
    const Icon = icons[idx % icons.length];
    return (
        <div className="flex items-center gap-2 bg-[#131722] border border-[#2b2b43] rounded-lg px-3 py-2 text-xs">
            <Icon size={14} className="text-[#2962FF]" />
            <span className="text-[#d1d4dc] font-medium">{stage}</span>
        </div>
    );
};

/* ── Main Component ─────────────────────────────────────────── */

const MLWorkflow = ({ portfolios }) => {
    const [selectedPortfolio, setSelectedPortfolio] = useState("");
    const [interval, setInterval_] = useState("1h");
    const [trainingDays, setTrainingDays] = useState(30);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [result, setResult] = useState(null);

    // Pipeline history
    const [historyLoading, setHistoryLoading] = useState(false);
    const [history, setHistory] = useState([]);
    const [showHistory, setShowHistory] = useState(false);

    // Experiments
    const [experiments, setExperiments] = useState([]);
    const [expLoading, setExpLoading] = useState(false);
    const [showExperiments, setShowExperiments] = useState(false);

    // Model Ranking
    const [rankingData, setRankingData] = useState(null);
    const [rankingLoading, setRankingLoading] = useState(false);

    // Monitoring Dashboard Data
    const [monitoringData, setMonitoringData] = useState(null);
    const [monitoringLoading, setMonitoringLoading] = useState(false);

    const fetchMonitoringData = async (portfolioId) => {
        setMonitoringLoading(true);
        try {
            const res = await api.get(`/api/ml_flow/monitoring/${portfolioId}/`);
            setMonitoringData(res.data);
        } catch {
            /* silent */
        } finally {
            setMonitoringLoading(false);
        }
    };

    const fetchModelRanking = async (portfolioId) => {
        setRankingLoading(true);
        try {
            const res = await api.get(`/api/ml_flow/model-ranking/${portfolioId}/`);
            setRankingData(res.data);
        } catch {
            /* silent */
        } finally {
            setRankingLoading(false);
        }
    };

    useEffect(() => {
        if (selectedPortfolio) {
            fetchModelRanking(selectedPortfolio);
            fetchMonitoringData(selectedPortfolio);
        } else {
            setRankingData(null);
            setMonitoringData(null);
        }
    }, [selectedPortfolio]);

    const runPipeline = async () => {
        if (!selectedPortfolio) {
            setError("Please select a portfolio.");
            return;
        }
        setLoading(true);
        setError("");
        setResult(null);

        try {
            const res = await api.post("/api/ml_flow/run-pipeline/", {
                portfolio_id: parseInt(selectedPortfolio),
                interval,
                training_days: trainingDays,
            });
            setResult(res.data);
            // Auto-fetch model ranking and monitoring after pipeline run
            fetchModelRanking(parseInt(selectedPortfolio));
            fetchMonitoringData(parseInt(selectedPortfolio));
        } catch (err) {
            const msg =
                err.response?.data?.error ||
                err.response?.data?.details ||
                "Pipeline execution failed.";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    const loadHistory = async () => {
        setShowHistory((prev) => !prev);
        if (history.length) return;
        setHistoryLoading(true);
        try {
            const res = await api.get("/api/ml_flow/pipeline-runs/");
            setHistory(res.data);
        } catch {
            /* silent */
        } finally {
            setHistoryLoading(false);
        }
    };

    const loadExperiments = async () => {
        setShowExperiments((prev) => !prev);
        if (experiments.length) return;
        setExpLoading(true);
        try {
            const res = await api.get("/api/ml_flow/experiments/");
            setExperiments(res.data.experiments || []);
        } catch {
            /* silent */
        } finally {
            setExpLoading(false);
        }
    };

    /* ── successful results (non-error stocks) ─────────────────── */
    const successStocks = result?.results?.filter((r) => !r.error) || [];
    const errorStocks = result?.results?.filter((r) => r.error) || [];

    /* ── chart data ────────────────────────────────────────────── */
    const priceComparisonData = successStocks.map((s) => ({
        ticker: s.ticker,
        current: s.current_price,
        predicted: s.predicted_price,
        change: pctChange(s.current_price, s.predicted_price),
    }));

    const modelMetricsData = (() => {
        if (!successStocks.length) return [];
        const allMetrics = successStocks[0]?.all_model_metrics || {};
        return Object.entries(allMetrics).map(([model, metrics]) => ({
            model,
            rmse: metrics.rmse,
            mae: metrics.mae,
            mse: metrics.mse,
            fill: MODEL_COLORS[model] || "#6366f1",
        }));
    })();

    /* ── radar data for model comparison ──────────────────────── */
    const radarData = (() => {
        if (!successStocks.length) return [];
        // Collect all unique models across all stocks
        const modelSet = new Set();
        successStocks.forEach((s) => {
            if (s.all_model_metrics) Object.keys(s.all_model_metrics).forEach((m) => modelSet.add(m));
        });
        // metrics: for each metric, show each model's normalized value
        const metrics = ["rmse", "mae"];
        return metrics.map((metric) => {
            const entry = { metric: metric.toUpperCase() };
            modelSet.forEach((model) => {
                // Average this metric across all stocks for this model
                const vals = successStocks
                    .map((s) => s.all_model_metrics?.[model]?.[metric])
                    .filter((v) => v != null);
                entry[model] = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
            });
            return entry;
        });
    })();

    const radarModels = radarData.length
        ? Object.keys(radarData[0]).filter((k) => k !== "metric")
        : [];

    const PIPELINE_STAGES = [
        "Data Ingestion",
        "Data Validation",
        "Feature Engineering",
        "Model Training",
        "Model Evaluation",
        "MLflow Tracking",
        "Prediction",
    ];

    return (
        <div className="space-y-6">
            {/* ── Header ─────────────────────────────────────────── */}
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
                    <Cpu size={20} className="text-white" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white tracking-tight">
                        ML Workflow Pipeline
                    </h2>
                    <p className="text-xs text-[#787b86]">
                        End-to-end MLOps — train, evaluate, and predict in one click
                    </p>
                </div>
            </div>

            {/* ── Pipeline Stages Visual ─────────────────────────── */}
            <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                <div className="text-xs text-[#787b86] uppercase tracking-wider mb-3 font-medium">
                    Pipeline Stages
                </div>
                <div className="flex flex-wrap gap-2">
                    {PIPELINE_STAGES.map((stage, i) => (
                        <React.Fragment key={stage}>
                            <PipelineStageBadge stage={stage} idx={i} />
                            {i < PIPELINE_STAGES.length - 1 && (
                                <div className="flex items-center text-[#2b2b43]">
                                    <ChevronRight size={16} />
                                </div>
                            )}
                        </React.Fragment>
                    ))}
                </div>
            </div>

            {/* ── Controls Card ──────────────────────────────────── */}
            <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-5 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Portfolio */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[#787b86] uppercase tracking-wider flex items-center gap-1.5">
                            <BarChart3 size={12} />
                            Portfolio
                        </label>
                        <select
                            value={selectedPortfolio}
                            onChange={(e) => setSelectedPortfolio(e.target.value)}
                            className="w-full bg-[#131722] border border-[#2b2b43] rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-[#2962FF] focus:ring-1 focus:ring-[#2962FF] transition-all appearance-none cursor-pointer"
                        >
                            <option value="">Select portfolio...</option>
                            {portfolios.map((p) => (
                                <option key={p.id} value={p.id}>
                                    {p.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Interval */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[#787b86] uppercase tracking-wider flex items-center gap-1.5">
                            <Clock size={12} />
                            Interval
                        </label>
                        <select
                            value={interval}
                            onChange={(e) => setInterval_(e.target.value)}
                            className="w-full bg-[#131722] border border-[#2b2b43] rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-[#2962FF] focus:ring-1 focus:ring-[#2962FF] transition-all appearance-none cursor-pointer"
                        >
                            <option value="1h">1 Hour</option>
                            <option value="1d">1 Day</option>
                            <option value="1wk">1 Week</option>
                        </select>
                    </div>

                    {/* Training Days */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[#787b86] uppercase tracking-wider flex items-center gap-1.5">
                            <Activity size={12} />
                            Training Days
                        </label>
                        <select
                            value={trainingDays}
                            onChange={(e) => setTrainingDays(parseInt(e.target.value))}
                            className="w-full bg-[#131722] border border-[#2b2b43] rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-[#2962FF] focus:ring-1 focus:ring-[#2962FF] transition-all appearance-none cursor-pointer"
                        >
                            <option value={7}>7 Days</option>
                            <option value={14}>14 Days</option>
                            <option value={30}>30 Days</option>
                            <option value={60}>60 Days</option>
                            <option value={90}>90 Days</option>
                        </select>
                    </div>

                    {/* Run Button */}
                    <div className="flex items-end">
                        <button
                            onClick={runPipeline}
                            disabled={loading}
                            className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-semibold py-2.5 px-5 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    Running Pipeline...
                                </>
                            ) : (
                                <>
                                    <Play size={16} />
                                    Run Pipeline
                                </>
                            )}
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="flex items-center gap-2 text-[#f23645] text-sm bg-[rgba(242,54,69,0.08)] border border-[rgba(242,54,69,0.2)] rounded-lg px-4 py-3">
                        <AlertCircle size={16} />
                        {error}
                    </div>
                )}
            </div>

            {/* ── Loading State ──────────────────────────────────── */}
            {loading && (
                <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-12 flex flex-col items-center justify-center gap-4">
                    <div className="relative">
                        <div className="w-16 h-16 rounded-full border-4 border-[#2b2b43] border-t-cyan-500 animate-spin" />
                        <div
                            className="absolute inset-0 w-16 h-16 rounded-full border-4 border-transparent border-b-blue-600 animate-spin"
                            style={{ animationDuration: "1.5s" }}
                        />
                    </div>
                    <div className="text-center">
                        <p className="text-white font-medium">
                            Executing ML Pipeline
                        </p>
                        <p className="text-xs text-[#787b86] mt-1">
                            Ingesting data → Validating → Engineering features → Training
                            models → Evaluating → Logging to MLflow...
                        </p>
                    </div>
                </div>
            )}

            {/* ──────────────────────────────────────────────────── */}
            {/* ── RESULTS ──────────────────────────────────────── */}
            {/* ──────────────────────────────────────────────────── */}
            {result && !loading && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">Portfolio</div>
                            <div className="text-lg font-bold text-white truncate">
                                {result.portfolio}
                            </div>
                        </div>
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">Stocks Analyzed</div>
                            <div className="text-2xl font-bold text-[#2962FF]">
                                {successStocks.length}
                            </div>
                        </div>
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">Models Trained</div>
                            <div className="text-2xl font-bold text-[#089981]">
                                {modelMetricsData.length}
                            </div>
                        </div>
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">Pipeline Run ID</div>
                            <div className="text-2xl font-bold text-[#6366f1]">
                                #{result.pipeline_run_id}
                            </div>
                        </div>
                    </div>

                    {/* ── Predictions Table ──────────────────────────── */}
                    <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                        <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                            <TrendingUp size={16} className="text-cyan-400" />
                            <h3 className="text-sm font-semibold text-white">
                                Stock Predictions
                            </h3>
                        </div>
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-[#2b2b43]">
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Ticker
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Current Price
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Predicted Price
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Change
                                        </th>
                                        <th className="px-3 py-3 text-center text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Best Model
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            RMSE
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            MAE
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {successStocks.map((stock, idx) => {
                                        const change = pctChange(
                                            stock.current_price,
                                            stock.predicted_price
                                        );
                                        const isUp = change >= 0;
                                        return (
                                            <tr
                                                key={stock.ticker}
                                                className={`border-b border-[#2b2b43]/50 hover:bg-[#2a2e39]/50 transition-colors ${idx % 2 === 0 ? "bg-[#1e222d]" : "bg-[#1a1e28]"
                                                    }`}
                                            >
                                                <td className="px-4 py-3">
                                                    <div className="font-semibold text-white">
                                                        {stock.ticker}
                                                    </div>
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono text-white">
                                                    ${stock.current_price?.toFixed(2)}
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono font-semibold"
                                                    style={{ color: isUp ? "#089981" : "#f23645" }}
                                                >
                                                    ${stock.predicted_price?.toFixed(2)}
                                                </td>
                                                <td className="px-3 py-3 text-right">
                                                    <span
                                                        className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${isUp
                                                            ? "bg-[rgba(8,153,129,0.15)] text-[#089981] border border-[rgba(8,153,129,0.3)]"
                                                            : "bg-[rgba(242,54,69,0.15)] text-[#f23645] border border-[rgba(242,54,69,0.3)]"
                                                            }`}
                                                    >
                                                        {isUp ? (
                                                            <TrendingUp size={12} />
                                                        ) : (
                                                            <TrendingDown size={12} />
                                                        )}
                                                        {isUp ? "+" : ""}
                                                        {change.toFixed(2)}%
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-center">
                                                    <span
                                                        className="text-xs font-semibold px-2.5 py-1 rounded-full border"
                                                        style={{
                                                            color:
                                                                MODEL_COLORS[stock.best_model] || "#d1d4dc",
                                                            borderColor:
                                                                (MODEL_COLORS[stock.best_model] || "#d1d4dc") +
                                                                "40",
                                                            backgroundColor:
                                                                (MODEL_COLORS[stock.best_model] || "#d1d4dc") +
                                                                "15",
                                                        }}
                                                    >
                                                        {stock.best_model}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono text-xs text-[#d1d4dc]">
                                                    {stock.metrics?.rmse?.toFixed(4)}
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono text-xs text-[#d1d4dc]">
                                                    {stock.metrics?.mae?.toFixed(4)}
                                                </td>
                                            </tr>
                                        );
                                    })}

                                    {/* Error stocks */}
                                    {errorStocks.map((stock) => (
                                        <tr
                                            key={stock.ticker}
                                            className="border-b border-[#2b2b43]/50 bg-[rgba(242,54,69,0.03)]"
                                        >
                                            <td className="px-4 py-3 font-semibold text-white">
                                                {stock.ticker}
                                            </td>
                                            <td
                                                colSpan={6}
                                                className="px-4 py-3 text-[#f23645] text-xs flex items-center gap-2"
                                            >
                                                <XCircle size={14} />
                                                {stock.error}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* ── Price Comparison Chart ──────────────────────── */}
                    {priceComparisonData.length > 0 && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                <BarChart3 size={16} className="text-[#2962FF]" />
                                <h3 className="text-sm font-semibold text-white">
                                    Price Comparison — Current vs Predicted
                                </h3>
                            </div>
                            <div className="p-5">
                                <ResponsiveContainer width="100%" height={320}>
                                    <BarChart data={priceComparisonData} barGap={4}>
                                        <CartesianGrid
                                            strokeDasharray="3 3"
                                            stroke="#2b2b43"
                                            vertical={false}
                                        />
                                        <XAxis
                                            dataKey="ticker"
                                            tick={{ fill: "#787b86", fontSize: 12 }}
                                            axisLine={{ stroke: "#2b2b43" }}
                                            tickLine={false}
                                        />
                                        <YAxis
                                            tick={{ fill: "#787b86", fontSize: 11 }}
                                            axisLine={false}
                                            tickLine={false}
                                            tickFormatter={(v) => `$${v}`}
                                        />
                                        <Tooltip
                                            contentStyle={{
                                                backgroundColor: "#1e222d",
                                                border: "1px solid #2b2b43",
                                                borderRadius: "8px",
                                                color: "#d1d4dc",
                                                fontSize: "12px",
                                            }}
                                            formatter={(val) => [`$${val.toFixed(2)}`]}
                                        />
                                        <Legend
                                            wrapperStyle={{ fontSize: "12px", color: "#787b86" }}
                                        />
                                        <Bar
                                            dataKey="current"
                                            name="Current Price"
                                            fill="#2962FF"
                                            radius={[4, 4, 0, 0]}
                                        />
                                        <Bar
                                            dataKey="predicted"
                                            name="Predicted Price"
                                            radius={[4, 4, 0, 0]}
                                        >
                                            {priceComparisonData.map((entry, index) => (
                                                <Cell
                                                    key={index}
                                                    fill={entry.change >= 0 ? "#089981" : "#f23645"}
                                                />
                                            ))}
                                        </Bar>
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}

                    {/* ── Model Metrics Comparison ────────────────────── */}
                    {modelMetricsData.length > 0 && (
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* RMSE/MAE Bar Chart */}
                            <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                                <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                    <Trophy size={16} className="text-[#f7931a]" />
                                    <h3 className="text-sm font-semibold text-white">
                                        Model Metrics (First Stock)
                                    </h3>
                                </div>
                                <div className="p-5">
                                    <div className="grid grid-cols-3 gap-3 mb-4">
                                        {modelMetricsData.map((m) => (
                                            <MetricPill
                                                key={m.model}
                                                label={m.model}
                                                value={m.rmse}
                                                color={m.fill}
                                            />
                                        ))}
                                    </div>
                                    <ResponsiveContainer width="100%" height={240}>
                                        <BarChart data={modelMetricsData} barGap={6}>
                                            <CartesianGrid
                                                strokeDasharray="3 3"
                                                stroke="#2b2b43"
                                                vertical={false}
                                            />
                                            <XAxis
                                                dataKey="model"
                                                tick={{ fill: "#787b86", fontSize: 11 }}
                                                axisLine={{ stroke: "#2b2b43" }}
                                                tickLine={false}
                                            />
                                            <YAxis
                                                tick={{ fill: "#787b86", fontSize: 11 }}
                                                axisLine={false}
                                                tickLine={false}
                                            />
                                            <Tooltip
                                                contentStyle={{
                                                    backgroundColor: "#1e222d",
                                                    border: "1px solid #2b2b43",
                                                    borderRadius: "8px",
                                                    color: "#d1d4dc",
                                                    fontSize: "12px",
                                                }}
                                            />
                                            <Legend
                                                wrapperStyle={{ fontSize: "12px", color: "#787b86" }}
                                            />
                                            <Bar
                                                dataKey="rmse"
                                                name="RMSE"
                                                radius={[4, 4, 0, 0]}
                                            >
                                                {modelMetricsData.map((entry, index) => (
                                                    <Cell key={index} fill={entry.fill} />
                                                ))}
                                            </Bar>
                                            <Bar
                                                dataKey="mae"
                                                name="MAE"
                                                fill="#787b86"
                                                radius={[4, 4, 0, 0]}
                                                opacity={0.6}
                                            />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Radar Chart */}
                            {radarData.length > 0 && (
                                <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                                    <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                        <Activity size={16} className="text-[#6366f1]" />
                                        <h3 className="text-sm font-semibold text-white">
                                            Model Comparison (Avg Across Stocks)
                                        </h3>
                                    </div>
                                    <div className="p-5 flex justify-center">
                                        <ResponsiveContainer width="100%" height={280}>
                                            <RadarChart data={radarData}>
                                                <PolarGrid stroke="#2b2b43" />
                                                <PolarAngleAxis
                                                    dataKey="metric"
                                                    tick={{ fill: "#787b86", fontSize: 11 }}
                                                />
                                                <PolarRadiusAxis
                                                    tick={{ fill: "#5d606b", fontSize: 10 }}
                                                    axisLine={false}
                                                />
                                                {radarModels.map((model) => (
                                                    <Radar
                                                        key={model}
                                                        name={model}
                                                        dataKey={model}
                                                        stroke={MODEL_COLORS[model] || "#6366f1"}
                                                        fill={MODEL_COLORS[model] || "#6366f1"}
                                                        fillOpacity={0.15}
                                                        strokeWidth={2}
                                                    />
                                                ))}
                                                <Legend
                                                    wrapperStyle={{ fontSize: "12px", color: "#787b86" }}
                                                />
                                            </RadarChart>
                                        </ResponsiveContainer>
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* ── Validation Reports ──────────────────────────── */}
                    {successStocks.some((s) => s.validation_report) && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                <CheckCircle2 size={16} className="text-[#089981]" />
                                <h3 className="text-sm font-semibold text-white">
                                    Data Validation Reports
                                </h3>
                            </div>
                            <div className="p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {successStocks.map((s) => {
                                    const rpt = s.validation_report;
                                    if (!rpt) return null;
                                    return (
                                        <div
                                            key={s.ticker}
                                            className="bg-[#131722] border border-[#2b2b43] rounded-lg p-4 space-y-2"
                                        >
                                            <div className="font-semibold text-white text-sm">
                                                {s.ticker}
                                            </div>
                                            <div className="flex gap-4 text-xs">
                                                <div>
                                                    <span className="text-[#787b86]">Original: </span>
                                                    <span className="text-[#d1d4dc] font-mono">
                                                        {rpt.original_rows}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-[#787b86]">Cleaned: </span>
                                                    <span className="text-[#089981] font-mono">
                                                        {rpt.cleaned_rows}
                                                    </span>
                                                </div>
                                                <div>
                                                    <span className="text-[#787b86]">Removed: </span>
                                                    <span className="text-[#f23645] font-mono">
                                                        {rpt.rows_removed}
                                                    </span>
                                                </div>
                                            </div>
                                            {rpt.issues?.length > 0 && (
                                                <div className="text-[10px] text-[#787b86] space-y-0.5">
                                                    {rpt.issues.map((issue, i) => (
                                                        <div key={i}>• {issue}</div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── VERIFICATION SUMMARY ─────────────────────────────── */}
            {result?.verification_summary && result.verification_summary.verified_count > 0 && !loading && (
                <div className="bg-gradient-to-r from-[rgba(8,153,129,0.1)] to-[rgba(41,98,255,0.1)] border border-[rgba(8,153,129,0.3)] rounded-xl p-4 flex items-center gap-3 animate-in fade-in duration-300">
                    <CheckCircle2 size={20} className="text-[#089981]" />
                    <div>
                        <div className="text-sm font-semibold text-[#089981]">
                            ✓ {result.verification_summary.verified_count} Previous Predictions Verified
                        </div>
                        <div className="text-xs text-[#787b86]">
                            Tickers: {result.verification_summary.tickers_verified?.join(", ")}
                        </div>
                    </div>
                </div>
            )}

            {/* ── MODEL RANKING & PREDICTIONS ────────────────────── */}
            {(rankingData?.model_ranking?.length > 0 || rankingData?.pending_predictions?.length > 0 || rankingData?.verified_predictions?.length > 0) && !loading && (
                <div className="space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {/* #1 Model Hero */}
                    {rankingData?.model_ranking?.length > 0 && (() => {
                        const winner = rankingData.model_ranking[0];
                        return (
                            <div className="relative overflow-hidden bg-gradient-to-br from-[#1e222d] via-[#1a1e28] to-[#131722] border border-[#f7931a]/30 rounded-2xl p-6">
                                {/* Glow effect */}
                                <div className="absolute top-0 right-0 w-40 h-40 bg-[#f7931a]/5 rounded-full blur-3xl" />
                                <div className="absolute bottom-0 left-0 w-32 h-32 bg-[#2962FF]/5 rounded-full blur-3xl" />

                                <div className="relative flex items-center justify-between">
                                    <div className="flex items-center gap-5">
                                        {/* Trophy */}
                                        <div className="relative">
                                            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#f7931a] to-[#e45a00] flex items-center justify-center shadow-xl shadow-[#f7931a]/20">
                                                <Trophy size={36} className="text-white" />
                                            </div>
                                            <div className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-gradient-to-br from-yellow-400 to-amber-500 flex items-center justify-center shadow-lg">
                                                <Crown size={14} className="text-white" />
                                            </div>
                                        </div>

                                        {/* Winner Info */}
                                        <div>
                                            <div className="text-xs text-[#787b86] uppercase tracking-wider font-medium mb-1">
                                                🏆 #1 Best Performing Model
                                            </div>
                                            <div className="text-4xl font-black text-white tracking-tight">
                                                {winner.model_name}
                                            </div>
                                            <div className="text-sm text-[#089981] font-semibold mt-1">
                                                Avg Error: {winner.avg_pct_error.toFixed(2)}% • {winner.total_predictions} predictions verified
                                            </div>
                                        </div>
                                    </div>

                                    {/* Stats */}
                                    <div className="hidden md:flex gap-4">
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-white">{winner.avg_pct_error.toFixed(2)}%</div>
                                            <div className="text-[10px] text-[#787b86] uppercase">Avg Error</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-[#089981]">{winner.min_pct_error.toFixed(2)}%</div>
                                            <div className="text-[10px] text-[#787b86] uppercase">Best</div>
                                        </div>
                                        <div className="text-center">
                                            <div className="text-2xl font-bold text-[#f23645]">{winner.max_pct_error.toFixed(2)}%</div>
                                            <div className="text-[10px] text-[#787b86] uppercase">Worst</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })()}

                    {/* All Models Ranking */}
                    {rankingData?.model_ranking?.length > 0 && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                <Medal size={16} className="text-[#f7931a]" />
                                <h3 className="text-sm font-semibold text-white">Model Ranking (by Prediction Accuracy)</h3>
                            </div>
                            <div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                                {rankingData.model_ranking.map((model) => {
                                    const rankColors = {
                                        1: { bg: "from-[#f7931a]/20 to-[#e45a00]/10", border: "border-[#f7931a]/40", badge: "bg-gradient-to-r from-[#f7931a] to-[#e45a00]" },
                                        2: { bg: "from-[#c0c0c0]/15 to-[#a0a0a0]/5", border: "border-[#c0c0c0]/30", badge: "bg-gradient-to-r from-gray-400 to-gray-500" },
                                        3: { bg: "from-[#cd7f32]/15 to-[#a0522d]/5", border: "border-[#cd7f32]/30", badge: "bg-gradient-to-r from-[#cd7f32] to-[#a0522d]" },
                                    };
                                    const rc = rankColors[model.rank] || { bg: "from-[#2b2b43]/30 to-transparent", border: "border-[#2b2b43]", badge: "bg-[#2b2b43]" };

                                    return (
                                        <div key={model.model_name} className={`bg-gradient-to-br ${rc.bg} border ${rc.border} rounded-xl p-4 relative overflow-hidden`}>
                                            {/* Rank Badge */}
                                            <div className={`absolute top-3 right-3 w-8 h-8 rounded-full ${rc.badge} flex items-center justify-center shadow-lg`}>
                                                <span className="text-white text-sm font-black">#{model.rank}</span>
                                            </div>

                                            <div className="text-lg font-bold text-white mb-3" style={{ color: MODEL_COLORS[model.model_name] || "#d1d4dc" }}>
                                                {model.model_name}
                                            </div>

                                            <div className="grid grid-cols-2 gap-2 text-xs">
                                                <div>
                                                    <div className="text-[#787b86]">Avg Error</div>
                                                    <div className="text-white font-mono font-semibold">{model.avg_pct_error.toFixed(2)}%</div>
                                                </div>
                                                <div>
                                                    <div className="text-[#787b86]">Avg Abs Error</div>
                                                    <div className="text-white font-mono font-semibold">${model.avg_abs_error.toFixed(4)}</div>
                                                </div>
                                                <div>
                                                    <div className="text-[#787b86]">Best</div>
                                                    <div className="text-[#089981] font-mono font-semibold">{model.min_pct_error.toFixed(2)}%</div>
                                                </div>
                                                <div>
                                                    <div className="text-[#787b86]">Worst</div>
                                                    <div className="text-[#f23645] font-mono font-semibold">{model.max_pct_error.toFixed(2)}%</div>
                                                </div>
                                                <div className="col-span-2">
                                                    <div className="text-[#787b86]">Predictions</div>
                                                    <div className="text-[#2962FF] font-mono font-semibold">{model.total_predictions}</div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    {/* Pending Predictions */}
                    {rankingData.pending_predictions?.length > 0 && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                <Timer size={16} className="text-[#f7931a]" />
                                <h3 className="text-sm font-semibold text-white">
                                    Pending Predictions ({rankingData.pending_predictions.length})
                                </h3>
                                <span className="text-[10px] text-[#787b86] ml-2">Will be verified on next run</span>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-[#2b2b43]">
                                            <th className="px-4 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Ticker</th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Model</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Price at Prediction</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Predicted Price</th>
                                            <th className="px-3 py-3 text-center text-xs font-semibold text-[#787b86] uppercase">Status</th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Predicted At</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rankingData.pending_predictions.map((p, idx) => (
                                            <tr key={p.id} className={`border-b border-[#2b2b43]/50 ${idx % 2 === 0 ? "bg-[#1e222d]" : "bg-[#1a1e28]"}`}>
                                                <td className="px-4 py-3 font-semibold text-white">{p.ticker}</td>
                                                <td className="px-3 py-3">
                                                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ color: MODEL_COLORS[p.model_name] || "#d1d4dc", backgroundColor: (MODEL_COLORS[p.model_name] || "#d1d4dc") + "15" }}>
                                                        {p.model_name}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono text-[#d1d4dc]">${p.current_price_at_prediction?.toFixed(2)}</td>
                                                <td className="px-3 py-3 text-right font-mono text-[#2962FF] font-semibold">${p.predicted_price?.toFixed(2)}</td>
                                                <td className="px-3 py-3 text-center">
                                                    <span className="text-xs px-2.5 py-1 rounded-full bg-[rgba(247,147,26,0.15)] text-[#f7931a] font-medium animate-pulse">
                                                        ⏳ Pending
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-xs text-[#787b86]">{new Date(p.predicted_at).toLocaleString()}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Verified Predictions */}
                    {rankingData.verified_predictions?.length > 0 && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                <Eye size={16} className="text-[#089981]" />
                                <h3 className="text-sm font-semibold text-white">Verified Predictions (Latest 50)</h3>
                            </div>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-[#2b2b43]">
                                            <th className="px-4 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Ticker</th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Model</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Predicted</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Actual</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Error %</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Abs Error</th>
                                            <th className="px-3 py-3 text-center text-xs font-semibold text-[#787b86] uppercase">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {rankingData.verified_predictions.map((p, idx) => (
                                            <tr key={p.id} className={`border-b border-[#2b2b43]/50 ${idx % 2 === 0 ? "bg-[#1e222d]" : "bg-[#1a1e28]"}`}>
                                                <td className="px-4 py-3 font-semibold text-white">{p.ticker}</td>
                                                <td className="px-3 py-3">
                                                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ color: MODEL_COLORS[p.model_name] || "#d1d4dc", backgroundColor: (MODEL_COLORS[p.model_name] || "#d1d4dc") + "15" }}>
                                                        {p.model_name}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono text-[#d1d4dc]">${p.predicted_price?.toFixed(2)}</td>
                                                <td className="px-3 py-3 text-right font-mono text-white font-semibold">${p.actual_price?.toFixed(2)}</td>
                                                <td className="px-3 py-3 text-right">
                                                    <span className={`font-mono font-semibold ${p.pct_error < 1 ? "text-[#089981]" : p.pct_error < 3 ? "text-[#f7931a]" : "text-[#f23645]"}`}>
                                                        {p.pct_error?.toFixed(2)}%
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono text-xs text-[#d1d4dc]">${p.absolute_error?.toFixed(4)}</td>
                                                <td className="px-3 py-3 text-center">
                                                    <span className="text-xs px-2.5 py-1 rounded-full bg-[rgba(8,153,129,0.15)] text-[#089981] font-medium">
                                                        ✓ Verified
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── SYSTEM MONITORING & TRENDS ────────────────────── */}
            {(monitoringData?.system_monitoring || monitoringData?.prediction_trends) && !loading && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 mt-8">
                    {/* 1. System Monitoring (Drift & Error Over Time) */}
                    <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                        <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                            <Activity size={16} className="text-[#f7931a]" />
                            <h3 className="text-sm font-semibold text-white">System Monitoring</h3>
                        </div>
                        <div className="p-5 space-y-6">
                            {/* Drift Alerts */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {monitoringData.system_monitoring.drift_status?.map((ds) => (
                                    <div key={ds.model_name} className={`p-4 rounded-xl border ${ds.drift_detected ? 'bg-[rgba(242,54,69,0.05)] border-[#f23645]/30' : 'bg-[rgba(8,153,129,0.05)] border-[#089981]/30'}`}>
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="font-semibold text-white" style={{ color: MODEL_COLORS[ds.model_name] || "#fff" }}>{ds.model_name}</span>
                                            {ds.drift_detected ? <ShieldAlert size={16} className="text-[#f23645]" /> : <ShieldCheck size={16} className="text-[#089981]" />}
                                        </div>
                                        <div className="text-xs text-[#787b86] mb-2">{ds.status}</div>
                                        <div className="flex justify-between text-xs">
                                            <span>Baseline: <span className="text-white font-mono">{ds.baseline_error}%</span></span>
                                            <span>Recent: <span className={ds.drift_detected ? "text-[#f23645] font-mono" : "text-white font-mono"}>{ds.recent_error}%</span></span>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Error Over Time Chart */}
                            {monitoringData.system_monitoring.error_over_time?.length > 0 && (
                                <div className="h-64 mt-4">
                                    <h4 className="text-xs text-[#787b86] uppercase tracking-wider mb-4">Prediction Error Over Time (%)</h4>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={monitoringData.system_monitoring.error_over_time}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#2b2b43" vertical={false} />
                                            <XAxis
                                                dataKey="timestamp"
                                                tickFormatter={(val) => new Date(val).toLocaleDateString()}
                                                stroke="#787b86"
                                                fontSize={10}
                                            />
                                            <YAxis stroke="#787b86" fontSize={10} tickFormatter={(val) => `${val}%`} />
                                            <Tooltip
                                                contentStyle={{ backgroundColor: "#1e222d", borderColor: "#2b2b43", borderRadius: "8px" }}
                                                labelFormatter={(val) => new Date(val).toLocaleString()}
                                            />
                                            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                                            {Object.keys(MODEL_COLORS).map(modelName => (
                                                <Line
                                                    key={modelName}
                                                    type="monotone"
                                                    dataKey={(row) => row.model_name === modelName ? row.pct_error : null}
                                                    name={modelName}
                                                    stroke={MODEL_COLORS[modelName]}
                                                    strokeWidth={2}
                                                    dot={{ r: 3, fill: MODEL_COLORS[modelName], strokeWidth: 0 }}
                                                    connectNulls={true}
                                                />
                                            ))}
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* 2. Prediction Trends */}
                    {monitoringData.prediction_trends && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <LineChartIcon size={16} className="text-[#2962FF]" />
                                    <h3 className="text-sm font-semibold text-white">Prediction Trends & Accuracy</h3>
                                </div>
                            </div>
                            <div className="p-5">
                                {/* Trend Stats */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                    <MetricPill label="Total Verified" value={monitoringData.prediction_trends.stats?.total_verified || 0} color="#fff" />
                                    <MetricPill label="Directional Acc." value={monitoringData.prediction_trends.stats?.directional_accuracy_pct || 0} unit="%" color="#089981" />
                                    <MetricPill label="Ensemble Error" value={monitoringData.prediction_trends.stats?.ensemble_error_pct || 0} unit="%" color="#f7931a" />
                                    <MetricPill label="Stability (Var)" value={monitoringData.prediction_trends.stats?.stability_variance || 0} color="#2962FF" />
                                </div>

                                {/* Actual vs Predicted Chart */}
                                {monitoringData.prediction_trends.actual_vs_predicted?.length > 0 && (
                                    <div className="h-72">
                                        <h4 className="text-xs text-[#787b86] uppercase tracking-wider mb-4">Actual vs Predicted Price ($)</h4>
                                        <ResponsiveContainer width="100%" height="100%">
                                            <LineChart data={monitoringData.prediction_trends.actual_vs_predicted}>
                                                <CartesianGrid strokeDasharray="3 3" stroke="#2b2b43" vertical={false} />
                                                <XAxis
                                                    dataKey="timestamp"
                                                    tickFormatter={(val) => new Date(val).toLocaleDateString()}
                                                    stroke="#787b86"
                                                    fontSize={10}
                                                />
                                                <YAxis stroke="#787b86" fontSize={10} domain={['auto', 'auto']} tickFormatter={(val) => `$${val}`} />
                                                <Tooltip
                                                    contentStyle={{ backgroundColor: "#1e222d", borderColor: "#2b2b43", borderRadius: "8px" }}
                                                    labelFormatter={(val) => new Date(val).toLocaleString()}
                                                />
                                                <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                                                <Line type="monotone" dataKey="actual" name="Actual Price" stroke="#fff" strokeWidth={3} dot={false} />
                                                {Object.keys(MODEL_COLORS).map(modelName => (
                                                    <Line
                                                        key={modelName}
                                                        type="monotone"
                                                        dataKey={(row) => row.model_name === modelName ? row.predicted : null}
                                                        name={`${modelName} Predicted`}
                                                        stroke={MODEL_COLORS[modelName]}
                                                        strokeWidth={1.5}
                                                        strokeDasharray="4 4"
                                                        dot={{ r: 2, fill: MODEL_COLORS[modelName], strokeWidth: 0 }}
                                                        connectNulls={true}
                                                    />
                                                ))}
                                            </LineChart>
                                        </ResponsiveContainer>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* 3. Predictions History */}
                    {monitoringData.predictions_history?.length > 0 && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                <History size={16} className="text-[#a0a0a0]" />
                                <h3 className="text-sm font-semibold text-white">Full Prediction History</h3>
                            </div>
                            <div className="overflow-x-auto max-h-96">
                                <table className="w-full text-sm">
                                    <thead className="sticky top-0 bg-[#1e222d] z-10 shadow-sm">
                                        <tr className="border-b border-[#2b2b43]">
                                            <th className="px-4 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Predicted At</th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Ticker</th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">Model</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Predicted</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Actual</th>
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">Error %</th>
                                            <th className="px-3 py-3 text-center text-xs font-semibold text-[#787b86] uppercase">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {monitoringData.predictions_history.map((p, idx) => (
                                            <tr key={p.id} className={`border-b border-[#2b2b43]/50 ${idx % 2 === 0 ? "bg-[#1e222d]" : "bg-[#1a1e28]"}`}>
                                                <td className="px-4 py-3 text-xs text-[#787b86]">{new Date(p.predicted_at).toLocaleString()}</td>
                                                <td className="px-3 py-3 font-semibold text-white">{p.ticker}</td>
                                                <td className="px-3 py-3">
                                                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ color: MODEL_COLORS[p.model_name] || "#d1d4dc", backgroundColor: (MODEL_COLORS[p.model_name] || "#d1d4dc") + "15" }}>
                                                        {p.model_name}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-right font-mono text-[#d1d4dc]">${p.predicted_price?.toFixed(2)}</td>
                                                <td className="px-3 py-3 text-right font-mono text-white">${p.actual_price ? p.actual_price.toFixed(2) : '-'}</td>
                                                <td className="px-3 py-3 text-right">
                                                    {p.pct_error != null ? (
                                                        <span className={`font-mono font-semibold ${p.pct_error < 1 ? "text-[#089981]" : p.pct_error < 3 ? "text-[#f7931a]" : "text-[#f23645]"}`}>
                                                            {p.pct_error?.toFixed(2)}%
                                                        </span>
                                                    ) : <span className="text-[#787b86]">-</span>}
                                                </td>
                                                <td className="px-3 py-3 text-center">
                                                    {p.status === 'verified' ? (
                                                        <span className="text-xs px-2 py-0.5 rounded-full bg-[rgba(8,153,129,0.15)] text-[#089981]">Verified</span>
                                                    ) : p.status === 'pending' ? (
                                                        <span className="text-xs px-2 py-0.5 rounded-full bg-[rgba(247,147,26,0.15)] text-[#f7931a] animate-pulse">Pending</span>
                                                    ) : (
                                                        <span className="text-xs px-2 py-0.5 rounded-full bg-[rgba(242,54,69,0.15)] text-[#f23645]">Expired</span>
                                                    )}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* ── Pipeline History (collapsible) ──────────────────── */}
            <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                <button
                    onClick={loadHistory}
                    className="w-full px-5 py-4 flex items-center justify-between hover:bg-[#2a2e39] transition-colors"
                >
                    <div className="flex items-center gap-2">
                        <History size={16} className="text-[#787b86]" />
                        <span className="text-sm font-semibold text-white">
                            Pipeline Run History
                        </span>
                    </div>
                    {showHistory ? (
                        <ChevronDown size={16} className="text-[#787b86]" />
                    ) : (
                        <ChevronRight size={16} className="text-[#787b86]" />
                    )}
                </button>

                {showHistory && (
                    <div className="border-t border-[#2b2b43]">
                        {historyLoading ? (
                            <div className="p-6 text-center text-[#787b86] text-sm">
                                <Loader2 size={20} className="animate-spin mx-auto mb-2" />
                                Loading...
                            </div>
                        ) : history.length === 0 ? (
                            <div className="p-6 text-center text-[#787b86] text-sm">
                                No pipeline runs yet.
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-[#2b2b43]">
                                            <th className="px-4 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">
                                                ID
                                            </th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">
                                                Portfolio
                                            </th>
                                            <th className="px-3 py-3 text-center text-xs font-semibold text-[#787b86] uppercase">
                                                Status
                                            </th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">
                                                Interval
                                            </th>
                                            <th className="px-3 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">
                                                Started
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {history.map((run, idx) => (
                                            <tr
                                                key={run.id}
                                                className={`border-b border-[#2b2b43]/50 ${idx % 2 === 0 ? "bg-[#1e222d]" : "bg-[#1a1e28]"
                                                    }`}
                                            >
                                                <td className="px-4 py-3 font-mono text-[#2962FF]">
                                                    #{run.id}
                                                </td>
                                                <td className="px-3 py-3 text-white">
                                                    {run.portfolio_name}
                                                </td>
                                                <td className="px-3 py-3 text-center">
                                                    <span
                                                        className={`text-xs px-2 py-0.5 rounded-full font-medium ${run.status === "completed"
                                                            ? "bg-[rgba(8,153,129,0.15)] text-[#089981]"
                                                            : run.status === "failed"
                                                                ? "bg-[rgba(242,54,69,0.15)] text-[#f23645]"
                                                                : "bg-[rgba(41,98,255,0.15)] text-[#2962FF]"
                                                            }`}
                                                    >
                                                        {run.status}
                                                    </span>
                                                </td>
                                                <td className="px-3 py-3 text-[#787b86] font-mono text-xs">
                                                    {run.interval} / {run.training_days}d
                                                </td>
                                                <td className="px-3 py-3 text-[#787b86] text-xs">
                                                    {new Date(run.started_at).toLocaleString()}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* ── Experiments (collapsible) ───────────────────────── */}
            <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                <button
                    onClick={loadExperiments}
                    className="w-full px-5 py-4 flex items-center justify-between hover:bg-[#2a2e39] transition-colors"
                >
                    <div className="flex items-center gap-2">
                        <FlaskConical size={16} className="text-[#787b86]" />
                        <span className="text-sm font-semibold text-white">
                            MLflow Experiments
                        </span>
                    </div>
                    {showExperiments ? (
                        <ChevronDown size={16} className="text-[#787b86]" />
                    ) : (
                        <ChevronRight size={16} className="text-[#787b86]" />
                    )}
                </button>

                {showExperiments && (
                    <div className="border-t border-[#2b2b43]">
                        {expLoading ? (
                            <div className="p-6 text-center text-[#787b86] text-sm">
                                <Loader2 size={20} className="animate-spin mx-auto mb-2" />
                                Loading...
                            </div>
                        ) : experiments.length === 0 ? (
                            <div className="p-6 text-center text-[#787b86] text-sm">
                                No experiments logged yet. Run the pipeline first!
                            </div>
                        ) : (
                            <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {experiments
                                    .filter((e) => e.name !== "Default")
                                    .map((exp) => (
                                        <div
                                            key={exp.experiment_id}
                                            className="bg-[#131722] border border-[#2b2b43] rounded-lg p-4"
                                        >
                                            <div className="flex items-center gap-2 mb-2">
                                                <FlaskConical size={14} className="text-[#6366f1]" />
                                                <span className="text-sm font-semibold text-white">
                                                    {exp.name}
                                                </span>
                                            </div>
                                            <div className="text-[10px] text-[#787b86] space-y-0.5">
                                                <div>ID: {exp.experiment_id}</div>
                                                <div>Stage: {exp.lifecycle_stage}</div>
                                            </div>
                                        </div>
                                    ))}
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default MLWorkflow;
