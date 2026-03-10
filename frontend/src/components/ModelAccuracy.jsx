import React, { useState } from "react";
import api from "../api/axios";
import {
    Activity,
    Calendar,
    Clock,
    Trophy,
    TrendingUp,
    TrendingDown,
    AlertCircle,
    Loader2,
    BarChart3,
    Target,
} from "lucide-react";

const MODEL_NAMES = ["Linear", "Logistic", "LSTM", "RNN", "CNN", "ARIMA"];

const MEDAL = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣"];

const HOURS = Array.from({ length: 24 }, (_, i) => {
    const h = i.toString().padStart(2, "0");
    return { value: `${h}:00`, label: `${h}:00` };
});

const SignalBadge = ({ signal }) => {
    if (!signal || signal === "N/A")
        return (
            <span className="text-xs px-2 py-0.5 rounded bg-[#2a2e39] text-[#787b86]">
                N/A
            </span>
        );
    const isUp = signal === "increase";
    return (
        <span
            className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${isUp
                    ? "bg-[rgba(8,153,129,0.15)] text-[#089981] border border-[rgba(8,153,129,0.3)]"
                    : "bg-[rgba(242,54,69,0.15)] text-[#f23645] border border-[rgba(242,54,69,0.3)]"
                }`}
        >
            {isUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {isUp ? "Increase" : "Decrease"}
        </span>
    );
};

const ModelAccuracy = ({ portfolios }) => {
    const [selectedPortfolio, setSelectedPortfolio] = useState("");
    const [targetDate, setTargetDate] = useState("");
    const [targetHour, setTargetHour] = useState("09:00");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [result, setResult] = useState(null);

    const runAnalysis = async () => {
        if (!selectedPortfolio || !targetDate || !targetHour) {
            setError("Please select a portfolio, date, and hour.");
            return;
        }

        setLoading(true);
        setError("");
        setResult(null);

        try {
            const res = await api.post("/api/analysis/model-accuracy/", {
                portfolio_id: selectedPortfolio,
                target_date: targetDate,
                target_hour: targetHour,
            });
            setResult(res.data);
        } catch (err) {
            const msg =
                err.response?.data?.error ||
                err.response?.data?.details ||
                "Analysis failed. Please try again.";
            setError(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-violet-600 to-fuchsia-500 flex items-center justify-center shadow-lg shadow-violet-500/20">
                    <Target size={20} className="text-white" />
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white tracking-tight">
                        Model Accuracy
                    </h2>
                    <p className="text-xs text-[#787b86]">
                        Evaluate 6 ML models on your portfolio stocks
                    </p>
                </div>
            </div>

            {/* Controls Card */}
            <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-5 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {/* Portfolio Select */}
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

                    {/* Date */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[#787b86] uppercase tracking-wider flex items-center gap-1.5">
                            <Calendar size={12} />
                            Target Date
                        </label>
                        <input
                            type="date"
                            value={targetDate}
                            onChange={(e) => setTargetDate(e.target.value)}
                            className="w-full bg-[#131722] border border-[#2b2b43] rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-[#2962FF] focus:ring-1 focus:ring-[#2962FF] transition-all cursor-pointer [color-scheme:dark]"
                        />
                    </div>

                    {/* Hour */}
                    <div className="space-y-1.5">
                        <label className="text-xs font-medium text-[#787b86] uppercase tracking-wider flex items-center gap-1.5">
                            <Clock size={12} />
                            Target Hour
                        </label>
                        <select
                            value={targetHour}
                            onChange={(e) => setTargetHour(e.target.value)}
                            className="w-full bg-[#131722] border border-[#2b2b43] rounded-lg px-3 py-2.5 text-sm text-white outline-none focus:border-[#2962FF] focus:ring-1 focus:ring-[#2962FF] transition-all appearance-none cursor-pointer"
                        >
                            {HOURS.map((h) => (
                                <option key={h.value} value={h.value}>
                                    {h.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Run Button */}
                    <div className="flex items-end">
                        <button
                            onClick={runAnalysis}
                            disabled={loading}
                            className="w-full bg-gradient-to-r from-[#2962FF] to-[#6366f1] hover:from-[#1e50e6] hover:to-[#5558e0] text-white font-semibold py-2.5 px-5 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-[#2962FF]/20 hover:shadow-[#2962FF]/30"
                        >
                            {loading ? (
                                <>
                                    <Loader2 size={16} className="animate-spin" />
                                    Analyzing...
                                </>
                            ) : (
                                <>
                                    <Activity size={16} />
                                    Run Analysis
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

            {/* Loading State */}
            {loading && (
                <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-12 flex flex-col items-center justify-center gap-4">
                    <div className="relative">
                        <div className="w-16 h-16 rounded-full border-4 border-[#2b2b43] border-t-[#2962FF] animate-spin" />
                        <div className="absolute inset-0 w-16 h-16 rounded-full border-4 border-transparent border-b-[#6366f1] animate-spin" style={{ animationDuration: "1.5s" }} />
                    </div>
                    <div className="text-center">
                        <p className="text-white font-medium">Running 6 ML Models</p>
                        <p className="text-xs text-[#787b86] mt-1">
                            Training & predicting on hourly data...
                        </p>
                    </div>
                </div>
            )}

            {/* Results */}
            {result && !loading && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {/* Summary Cards */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">Total Stocks</div>
                            <div className="text-2xl font-bold text-white">
                                {result.analysis?.total_stocks || 0}
                            </div>
                        </div>
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">With Data</div>
                            <div className="text-2xl font-bold text-[#089981]">
                                {result.analysis?.stocks_with_data || 0}
                            </div>
                        </div>
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">Models Used</div>
                            <div className="text-2xl font-bold text-[#6366f1]">6</div>
                        </div>
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl p-4">
                            <div className="text-xs text-[#787b86] mb-1">Actual Data</div>
                            <div className="text-2xl font-bold">
                                {result.analysis?.has_actual_prices ? (
                                    <span className="text-[#089981]">Available</span>
                                ) : (
                                    <span className="text-[#f7931a]">Forecast Only</span>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Results Table */}
                    <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                        <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                            <BarChart3 size={16} className="text-[#2962FF]" />
                            <h3 className="text-sm font-semibold text-white">
                                Prediction Results
                            </h3>
                        </div>

                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-[#2b2b43]">
                                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#787b86] uppercase tracking-wider sticky left-0 bg-[#1e222d] z-10">
                                            Stock
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Current
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Min
                                        </th>
                                        <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase tracking-wider">
                                            Max
                                        </th>
                                        {result.analysis?.has_actual_prices && (
                                            <th className="px-3 py-3 text-right text-xs font-semibold text-[#f7931a] uppercase tracking-wider">
                                                Actual
                                            </th>
                                        )}
                                        {MODEL_NAMES.map((m) => (
                                            <th
                                                key={m}
                                                className="px-3 py-3 text-center text-xs font-semibold text-[#787b86] uppercase tracking-wider"
                                                colSpan={3}
                                            >
                                                <span className="bg-[#2a2e39] px-2 py-1 rounded text-[#d1d4dc]">
                                                    {m}
                                                </span>
                                            </th>
                                        ))}
                                    </tr>
                                    <tr className="border-b border-[#2b2b43] bg-[#181c27]">
                                        <th className="sticky left-0 bg-[#181c27] z-10" />
                                        <th />
                                        <th />
                                        <th />
                                        {result.analysis?.has_actual_prices && <th />}
                                        {MODEL_NAMES.map((m) => (
                                            <React.Fragment key={`sub-${m}`}>
                                                <th className="px-2 py-2 text-[10px] text-[#5d606b] font-medium">
                                                    Pred
                                                </th>
                                                <th className="px-2 py-2 text-[10px] text-[#5d606b] font-medium">
                                                    Chg
                                                </th>
                                                <th className="px-2 py-2 text-[10px] text-[#5d606b] font-medium">
                                                    Signal
                                                </th>
                                            </React.Fragment>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {result.stocks?.map((stock, idx) => (
                                        <tr
                                            key={stock.stock_ticker}
                                            className={`border-b border-[#2b2b43]/50 hover:bg-[#2a2e39]/50 transition-colors ${idx % 2 === 0 ? "bg-[#1e222d]" : "bg-[#1a1e28]"
                                                }`}
                                        >
                                            <td className="px-4 py-3 sticky left-0 bg-inherit z-10">
                                                <div className="font-semibold text-white">
                                                    {stock.stock_ticker}
                                                </div>
                                                <div className="text-[10px] text-[#787b86] truncate max-w-[120px]">
                                                    {stock.stock_name}
                                                </div>
                                            </td>
                                            <td className="px-3 py-3 text-right font-mono text-white">
                                                {stock.error
                                                    ? "—"
                                                    : `$${stock.current_price?.toFixed(2)}`}
                                            </td>
                                            <td className="px-3 py-3 text-right font-mono text-[#787b86]">
                                                {stock.error
                                                    ? "—"
                                                    : `$${stock.min_price?.toFixed(2)}`}
                                            </td>
                                            <td className="px-3 py-3 text-right font-mono text-[#787b86]">
                                                {stock.error
                                                    ? "—"
                                                    : `$${stock.max_price?.toFixed(2)}`}
                                            </td>
                                            {result.analysis?.has_actual_prices && (
                                                <td className="px-3 py-3 text-right font-mono text-[#f7931a] font-semibold">
                                                    {stock.actual_price
                                                        ? `$${stock.actual_price?.toFixed(2)}`
                                                        : "—"}
                                                </td>
                                            )}
                                            {stock.error ? (
                                                <td
                                                    colSpan={MODEL_NAMES.length * 3}
                                                    className="px-4 py-3 text-center text-[#f23645] text-xs"
                                                >
                                                    {stock.error}
                                                </td>
                                            ) : (
                                                MODEL_NAMES.map((m) => {
                                                    const md = stock.models?.[m];
                                                    return (
                                                        <React.Fragment key={m}>
                                                            <td className="px-2 py-3 text-right font-mono text-xs text-[#d1d4dc]">
                                                                {md?.predicted_score != null
                                                                    ? `$${md.predicted_score.toFixed(2)}`
                                                                    : "—"}
                                                            </td>
                                                            <td
                                                                className={`px-2 py-3 text-right font-mono text-xs ${md?.change > 0
                                                                        ? "text-[#089981]"
                                                                        : md?.change < 0
                                                                            ? "text-[#f23645]"
                                                                            : "text-[#787b86]"
                                                                    }`}
                                                            >
                                                                {md?.change != null
                                                                    ? `${md.change > 0 ? "+" : ""}${md.change.toFixed(2)}`
                                                                    : "—"}
                                                            </td>
                                                            <td className="px-2 py-3 text-center">
                                                                <SignalBadge signal={md?.signal} />
                                                            </td>
                                                        </React.Fragment>
                                                    );
                                                })
                                            )}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Model Ranking (only when actual prices available) */}
                    {result.model_ranking && result.model_ranking.length > 0 && (
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                            <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                <Trophy size={16} className="text-[#f7931a]" />
                                <h3 className="text-sm font-semibold text-white">
                                    Model Accuracy Ranking
                                </h3>
                                <span className="text-[10px] text-[#787b86] ml-2">
                                    Based on RMSE (lower is better)
                                </span>
                            </div>

                            <div className="p-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {result.model_ranking.map((m, i) => (
                                    <div
                                        key={m.model}
                                        className={`relative rounded-xl p-4 border transition-all duration-300 hover:scale-[1.02] ${i === 0
                                                ? "bg-gradient-to-br from-[#f7931a]/10 to-[#f7931a]/5 border-[#f7931a]/30 shadow-lg shadow-[#f7931a]/5"
                                                : i === 1
                                                    ? "bg-gradient-to-br from-[#c0c0c0]/10 to-[#c0c0c0]/5 border-[#c0c0c0]/20"
                                                    : i === 2
                                                        ? "bg-gradient-to-br from-[#cd7f32]/10 to-[#cd7f32]/5 border-[#cd7f32]/20"
                                                        : "bg-[#131722] border-[#2b2b43]"
                                            }`}
                                    >
                                        <div className="flex items-center gap-3 mb-3">
                                            <span className="text-2xl">{MEDAL[i]}</span>
                                            <div>
                                                <div className="font-bold text-white text-base">
                                                    {m.model}
                                                </div>
                                                <div className="text-[10px] text-[#787b86]">
                                                    Rank #{m.rank}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="grid grid-cols-3 gap-2 text-center">
                                            <div>
                                                <div className="text-[10px] text-[#787b86] mb-0.5">
                                                    RMSE
                                                </div>
                                                <div className="text-sm font-mono font-semibold text-[#d1d4dc]">
                                                    {m.rmse?.toFixed(2)}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-[#787b86] mb-0.5">
                                                    MAE
                                                </div>
                                                <div className="text-sm font-mono font-semibold text-[#d1d4dc]">
                                                    {m.mae?.toFixed(2)}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-[10px] text-[#787b86] mb-0.5">
                                                    MAPE
                                                </div>
                                                <div className="text-sm font-mono font-semibold text-[#d1d4dc]">
                                                    {m.mape?.toFixed(2)}%
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Per-Stock Accuracy Details */}
                    {result.analysis?.has_actual_prices &&
                        result.stocks?.some((s) => s.accuracy_metrics) && (
                            <div className="bg-[#1e222d] border border-[#2b2b43] rounded-xl overflow-hidden">
                                <div className="px-5 py-4 border-b border-[#2b2b43] flex items-center gap-2">
                                    <Target size={16} className="text-[#6366f1]" />
                                    <h3 className="text-sm font-semibold text-white">
                                        Per-Stock Accuracy Metrics
                                    </h3>
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-[#2b2b43]">
                                                <th className="px-4 py-3 text-left text-xs font-semibold text-[#787b86] uppercase">
                                                    Stock
                                                </th>
                                                <th className="px-3 py-3 text-right text-xs font-semibold text-[#787b86] uppercase">
                                                    Actual
                                                </th>
                                                {MODEL_NAMES.map((m) => (
                                                    <th
                                                        key={m}
                                                        className="px-3 py-3 text-center text-xs font-semibold text-[#787b86] uppercase"
                                                    >
                                                        {m} Error
                                                    </th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {result.stocks
                                                ?.filter((s) => s.accuracy_metrics)
                                                .map((stock, idx) => (
                                                    <tr
                                                        key={stock.stock_ticker}
                                                        className={`border-b border-[#2b2b43]/50 ${idx % 2 === 0 ? "bg-[#1e222d]" : "bg-[#1a1e28]"
                                                            }`}
                                                    >
                                                        <td className="px-4 py-3 font-semibold text-white">
                                                            {stock.stock_ticker}
                                                        </td>
                                                        <td className="px-3 py-3 text-right font-mono text-[#f7931a]">
                                                            ${stock.actual_price?.toFixed(2)}
                                                        </td>
                                                        {MODEL_NAMES.map((m) => {
                                                            const am = stock.accuracy_metrics?.[m];
                                                            return (
                                                                <td
                                                                    key={m}
                                                                    className="px-3 py-3 text-center"
                                                                >
                                                                    {am ? (
                                                                        <div className="space-y-0.5">
                                                                            <div className="text-xs font-mono text-[#d1d4dc]">
                                                                                RMSE: {am.rmse?.toFixed(2)}
                                                                            </div>
                                                                            <div className="text-[10px] font-mono text-[#787b86]">
                                                                                MAPE: {am.mape?.toFixed(2)}%
                                                                            </div>
                                                                        </div>
                                                                    ) : (
                                                                        <span className="text-[#787b86]">—</span>
                                                                    )}
                                                                </td>
                                                            );
                                                        })}
                                                    </tr>
                                                ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                </div>
            )}
        </div>
    );
};

export default ModelAccuracy;
