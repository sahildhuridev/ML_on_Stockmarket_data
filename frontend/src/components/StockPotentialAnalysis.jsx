import React, { useState, useMemo, useEffect, useRef } from "react";
import api from "../api/axios";
import Spinner from "./Spinner";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Brush
} from "recharts";

const StockPotentialAnalysis = ({ portfolios }) => {
    const [selectedPortfolio, setSelectedPortfolio] = useState("all");
    const [timeframe, setTimeframe] = useState("1y");
    const [timeframeLabel, setTimeframeLabel] = useState("1-Year");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");

    // For chart selection
    const [selectedTicker, setSelectedTicker] = useState("");

    const hasRunOnce = useRef(false);

    const runAnalysis = async (tfOverride) => {
        setLoading(true);
        setError("");
        setResult(null);
        setSelectedTicker("");

        const tf = tfOverride || timeframe;

        try {
            const res = await api.get(`/api/analysis/stock-potential/?portfolio_id=${selectedPortfolio}&timeframe=${tf}`);
            setResult(res.data.results);
            setTimeframeLabel(res.data.timeframe_label || "1-Year");

            if (res.data.results && res.data.results.length > 0) {
                setSelectedTicker(res.data.results[0].ticker);
            }
            hasRunOnce.current = true;
        } catch (err) {
            setError(err.response?.data?.error || "Error running stock potential analysis.");
        } finally {
            setLoading(false);
        }
    };

    // Auto re-fetch when timeframe changes (only after first manual run)
    useEffect(() => {
        if (hasRunOnce.current) {
            runAnalysis(timeframe);
        }
        // eslint-disable-next-line
    }, [timeframe]);

    // Get chart data for the currently selected ticker
    const activeChartData = useMemo(() => {
        if (!result || !selectedTicker) return [];
        const stockData = result.find(s => s.ticker === selectedTicker);
        if (!stockData || !stockData.chart_data) return [];

        const data = [...stockData.chart_data];
        let lastActualIndex = -1;
        for (let i = data.length - 1; i >= 0; i--) {
            if (data[i].actual !== null && data[i].actual !== undefined) {
                lastActualIndex = i;
                break;
            }
        }

        if (lastActualIndex !== -1) {
            // Nullify the trend line for all dates BEFORE the last actual price
            for (let i = 0; i < lastActualIndex; i++) {
                data[i] = { ...data[i], trend: null };
            }

            // Snap the first point of the future trend line to exactly match the last actual price
            data[lastActualIndex] = {
                ...data[lastActualIndex],
                trend: data[lastActualIndex].actual
            };
        }

        return data;
    }, [result, selectedTicker]);

    return (
        <div className="h-full flex flex-col">
            <div className="p-4 border-b border-[#2b2b43] bg-[#1e222d] flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-lg font-semibold text-white tracking-wide">Stock Potential (Lin-Reg) 🎯</h2>
                    <p className="text-[#787b86] text-xs mt-1">
                        Predicts future {timeframeLabel.toLowerCase()} continuous price and expected returns using historical trendlines.
                    </p>
                </div>

                <div className="flex flex-wrap gap-4 items-center">
                    <div className="flex items-center space-x-2">
                        <select
                            className="bg-[#131722] border border-[#2b2b43] text-[#d1d4dc] text-sm rounded px-3 py-1.5 focus:outline-none focus:border-[#089981]"
                            value={selectedPortfolio}
                            onChange={(e) => setSelectedPortfolio(e.target.value)}
                        >
                            <option value="all">All Portfolios</option>
                            {portfolios && portfolios.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                    </div>

                    {/* Timeframe Selector */}
                    <div className="flex bg-[#131722] border border-[#2b2b43] rounded overflow-hidden">
                        {[
                            { key: '1w', label: '1W' },
                            { key: '1m', label: '1M' },
                            { key: '3m', label: '3M' },
                            { key: '1y', label: '1Y' },
                        ].map(tf => (
                            <button
                                key={tf.key}
                                onClick={() => setTimeframe(tf.key)}
                                className={`px-3 py-1.5 text-xs font-semibold transition-colors ${timeframe === tf.key
                                    ? 'bg-[#089981]/20 text-[#089981] border-b-2 border-[#089981]'
                                    : 'text-[#787b86] hover:bg-[#1e222d] hover:text-white'
                                    }`}
                            >
                                {tf.label}
                            </button>
                        ))}
                    </div>

                    <div className="flex items-center gap-2">
                        {result && (
                            <button
                                onClick={() => setResult(null)}
                                className="text-xs text-[#787b86] hover:text-[#f23645] px-3 py-1.5 transition-colors border border-transparent hover:border-[#f23645]/30 rounded bg-transparent"
                            >
                                Clear
                            </button>
                        )}
                        <button
                            onClick={() => runAnalysis()}
                            className="bg-[#089981] hover:bg-[#067a67] text-white text-sm font-medium py-1.5 px-4 rounded transition shadow-[0_0_10px_rgba(8,153,129,0.2)] hover:shadow-[0_0_15px_rgba(8,153,129,0.4)]"
                            disabled={loading}
                        >
                            {loading ? "Calculating..." : "Run Analysis"}
                        </button>
                    </div>
                </div>
            </div>

            <div className="flex-1 p-4 bg-[#131722] overflow-auto">
                {loading && <div className="mt-8 flex justify-center"><Spinner /></div>}

                {error && (
                    <div className="bg-[#f23645]/10 text-[#f23645] border border-[#f23645]/30 p-3 rounded text-sm mt-4">
                        {error}
                    </div>
                )}

                {result && (
                    <div className="space-y-6 animate-in fade-in duration-500">

                        {/* Chart Section */}
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-lg overflow-hidden shadow-lg p-4">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-sm font-semibold text-white tracking-wide">{timeframeLabel} Price Projection</h3>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-[#787b86]">View Chart For:</span>
                                    <select
                                        className="bg-[#131722] border border-[#2b2b43] text-[#089981] font-bold text-xs rounded px-2 py-1 focus:outline-none focus:border-[#089981]"
                                        value={selectedTicker}
                                        onChange={(e) => setSelectedTicker(e.target.value)}
                                    >
                                        {result.map(r => (
                                            <option key={r.ticker} value={r.ticker}>{r.ticker}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="w-full h-[350px]">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart
                                        data={activeChartData}
                                        margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
                                    >
                                        <CartesianGrid strokeDasharray="3 3" stroke="#2b2b43" opacity={0.5} vertical={false} />
                                        <XAxis
                                            dataKey="date"
                                            tick={{ fill: '#787b86', fontSize: 11 }}
                                            axisLine={{ stroke: '#2b2b43' }}
                                            tickLine={{ stroke: '#2b2b43' }}
                                            minTickGap={30}
                                        />
                                        <YAxis
                                            domain={['auto', 'auto']}
                                            tickFormatter={(val) => `$${val}`}
                                            tick={{ fill: '#787b86', fontSize: 11 }}
                                            axisLine={{ stroke: '#2b2b43' }}
                                            tickLine={{ stroke: '#2b2b43' }}
                                        />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1e222d', borderColor: '#2b2b43', color: '#d1d4dc', fontSize: '12px' }}
                                            formatter={(value) => [`$${parseFloat(value).toFixed(2)}`, ""]}
                                        />
                                        <Legend wrapperStyle={{ fontSize: '12px', color: '#d1d4dc' }} />
                                        <Line
                                            type="monotone"
                                            dataKey="actual"
                                            name="Actual Price"
                                            stroke="#2962FF"
                                            strokeWidth={2}
                                            dot={false}
                                            connectNulls={false}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="trend"
                                            name="Predicted Trend"
                                            stroke="#089981"
                                            strokeWidth={2}
                                            strokeDasharray="4 4"
                                            dot={false}
                                        />
                                        <Brush
                                            dataKey="date"
                                            height={30}
                                            stroke="#089981"
                                            fill="#1e222d"
                                            tickFormatter={() => ''}
                                            travellerWidth={8}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Table Section */}
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-lg overflow-hidden shadow-lg">
                            <div className="p-3 border-b border-[#2b2b43] bg-[#181c25]">
                                <h3 className="text-sm font-semibold text-white tracking-wide">Stock Expected Returns</h3>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="min-w-full text-xs text-left">
                                    <thead className="bg-[#131722] text-[#787b86] uppercase tracking-wider text-[10px]">
                                        <tr>
                                            <th className="px-4 py-2 font-medium">Symbol</th>
                                            <th className="px-4 py-2 font-medium">Current Price</th>
                                            <th className="px-4 py-2 font-medium">{timeframeLabel} Target</th>
                                            <th className="px-4 py-2 font-medium">Return</th>
                                            <th className="px-4 py-2 font-medium text-center">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[#2b2b43]">
                                        {result.map((row) => {
                                            const isPositive = row.expected_return >= 0;
                                            return (
                                                <tr key={row.ticker} className={`border-b border-[#2b2b43] hover:bg-[#2a2e39] transition-colors group ${selectedTicker === row.ticker ? "bg-[rgba(8,153,129,0.05)]" : ""}`}>
                                                    <td className="px-4 py-3 font-bold text-white group-hover:text-[#089981] transition-colors">{row.ticker}</td>
                                                    <td className="px-4 py-3 text-[#d1d4dc]">${row.current_price}</td>
                                                    <td className="px-4 py-3 text-[#d1d4dc]">${row.predicted_price}</td>
                                                    <td className="px-4 py-3">
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wide border
                                                            ${isPositive ? "bg-[rgba(8,153,129,0.1)] text-[#089981] border-[#089981]/30" : "bg-[rgba(242,54,69,0.1)] text-[#f23645] border-[#f23645]/30"}
                                                        `}>
                                                            {isPositive ? "▲" : "▼"} {isPositive ? "+" : ""}{row.expected_return}%
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-center">
                                                        <button
                                                            onClick={() => setSelectedTicker(row.ticker)}
                                                            className={`text-[10px] uppercase font-bold tracking-wider py-1 px-3 rounded transition-all border
                                                                ${selectedTicker === row.ticker
                                                                    ? "bg-[#089981]/20 text-[#089981] border-[#089981]/50"
                                                                    : "bg-transparent text-[#787b86] border-[#2b2b43] hover:text-white hover:border-[#5d606b]"}
                                                            `}
                                                        >
                                                            {selectedTicker === row.ticker ? "Active" : "Plot Chart"}
                                                        </button>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default StockPotentialAnalysis;
