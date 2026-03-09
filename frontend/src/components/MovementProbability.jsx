import React, { useState, useMemo } from "react";
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
import api from "../api/axios";
import Spinner from "./Spinner";

const MovementProbability = ({ portfolios }) => {
    const [selectedPortfolio, setSelectedPortfolio] = useState("all");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");
    const [selectedTicker, setSelectedTicker] = useState("");

    const runAnalysis = async () => {
        setLoading(true);
        setError("");
        setResult(null);
        setSelectedTicker("");

        try {
            const res = await api.get(`/api/analysis/movement-probability/?portfolio_id=${selectedPortfolio}`);
            setResult(res.data.results);
            if (res.data.results && res.data.results.length > 0) {
                setSelectedTicker(res.data.results[0].ticker);
            }
        } catch (err) {
            setError(err.response?.data?.error || "Error running movement probability analysis.");
        } finally {
            setLoading(false);
        }
    };

    const activeChartData = useMemo(() => {
        if (!result || !selectedTicker) return [];
        const stockData = result.find(s => s.ticker === selectedTicker);
        if (!stockData || !stockData.chart_data) return [];

        // Format data so lines connect perfectly
        const data = [...stockData.chart_data];
        let lastActualIndex = data.length - 2; // Second to last is the last actual price

        if (lastActualIndex >= 0) {
            const lastPrice = data[lastActualIndex].actual;
            // Snap predictions to the exact end point of 'actual'
            data[lastActualIndex] = {
                ...data[lastActualIndex],
                lr_pred: lastPrice,
                lstm_pred: lastPrice
            };
        }
        return data;
    }, [result, selectedTicker]);

    return (
        <div className="h-full flex flex-col">
            <div className="p-4 border-b border-[#2b2b43] bg-[#1e222d] flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-lg font-semibold text-white tracking-wide">Movement Probability (LSTM) 📈</h2>
                    <p className="text-[#787b86] text-xs mt-1">
                        Predicts whether the stock will go UP or DOWN in the very next trading session using TensorFlow sequences.
                    </p>
                </div>

                <div className="flex flex-wrap gap-4 items-center">
                    <div className="flex items-center space-x-2">
                        <select
                            className="bg-[#131722] border border-[#2b2b43] text-[#d1d4dc] text-sm rounded px-3 py-1.5 focus:outline-none focus:border-[#2962FF]"
                            value={selectedPortfolio}
                            onChange={(e) => setSelectedPortfolio(e.target.value)}
                        >
                            <option value="all">All Portfolios</option>
                            {portfolios && portfolios.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
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
                            onClick={runAnalysis}
                            className="bg-[#2962FF] hover:bg-[#1e53e5] text-white text-sm font-medium py-1.5 px-4 rounded transition shadow-[0_0_10px_rgba(41,98,255,0.2)] hover:shadow-[0_0_15px_rgba(41,98,255,0.4)]"
                            disabled={loading}
                        >
                            {loading ? "Calculating..." : "Run Probability Analysis"}
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
                                <h3 className="text-sm font-semibold text-white tracking-wide">Next Session Projection</h3>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-[#787b86]">View Chart For:</span>
                                    <select
                                        className="bg-[#131722] border border-[#2b2b43] text-[#2962FF] font-bold text-xs rounded px-2 py-1 focus:outline-none focus:border-[#2962FF]"
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
                                            name="Historical Actual Price"
                                            stroke="#d1d4dc"
                                            strokeWidth={2}
                                            dot={false}
                                            connectNulls={false}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="lr_pred"
                                            name="Prediction (Logistic Reg)"
                                            stroke="#2962FF"
                                            strokeWidth={2}
                                            strokeDasharray="4 4"
                                            dot={{ r: 4 }}
                                        />
                                        <Line
                                            type="monotone"
                                            dataKey="lstm_pred"
                                            name="Prediction (LSTM)"
                                            stroke="#8b5cf6"
                                            strokeWidth={2}
                                            strokeDasharray="4 4"
                                            dot={{ r: 4 }}
                                        />
                                        <Brush
                                            dataKey="date"
                                            height={30}
                                            stroke="#2962FF"
                                            fill="#1e222d"
                                            tickFormatter={() => ''}
                                            travellerWidth={8}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-lg overflow-hidden shadow-lg">
                            <div className="p-3 border-b border-[#2b2b43] bg-[#181c25]">
                                <h3 className="text-sm font-semibold text-white tracking-wide">Next Session Probability Details</h3>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="min-w-full text-xs text-left">
                                    <thead className="bg-[#131722] text-[#787b86] uppercase tracking-wider text-[10px]">
                                        <tr>
                                            <th className="px-4 py-2 font-medium">Symbol</th>
                                            <th className="px-4 py-2 font-medium">Logistic Model (UP)</th>
                                            <th className="px-4 py-2 font-medium">LSTM Neural Net (UP)</th>
                                            <th className="px-4 py-2 font-medium">1-Day Potential</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[#2b2b43]">
                                        {result.map((row) => {
                                            const expectedReturnStr = row.expected_return > 0 ? `+${row.expected_return}%` : `${row.expected_return}%`;
                                            const isPositiveReturn = row.expected_return >= 0;

                                            return (
                                                <tr key={row.ticker} className="border-b border-[#2b2b43] hover:bg-[#2a2e39] transition-colors group">
                                                    <td className="px-4 py-4 font-bold text-white group-hover:text-[#2962FF] transition-colors">{row.ticker}</td>

                                                    <td className="px-4 py-4">
                                                        <div className="flex items-center w-full">
                                                            <div className="w-full bg-[#131722] rounded-full h-1.5 mr-3 border border-[#2b2b43]">
                                                                <div className="bg-[#2962FF] h-1.5 rounded-full shadow-[0_0_8px_rgba(41,98,255,0.6)]" style={{ width: `${row.lr_prob_up}%` }}></div>
                                                            </div>
                                                            <span className="text-[10px] font-mono text-[#d1d4dc] min-w-[35px]">{row.lr_prob_up}%</span>
                                                        </div>
                                                    </td>

                                                    <td className="px-4 py-4">
                                                        <div className="flex items-center w-full">
                                                            <div className="w-full bg-[#131722] rounded-full h-1.5 mr-3 border border-[#2b2b43]">
                                                                <div className="bg-[#8b5cf6] h-1.5 rounded-full shadow-[0_0_8px_rgba(139,92,246,0.6)]" style={{ width: `${row.lstm_prob_up}%` }}></div>
                                                            </div>
                                                            <span className="text-[10px] font-mono text-[#d1d4dc] min-w-[35px]">{row.lstm_prob_up}%</span>
                                                        </div>
                                                    </td>

                                                    <td className="px-4 py-4 flex items-center">
                                                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wide border mr-2
                                                            ${isPositiveReturn ? "bg-[rgba(8,153,129,0.1)] text-[#089981] border-[#089981]/30" : "bg-[rgba(242,54,69,0.1)] text-[#f23645] border-[#f23645]/30"}
                                                        `}>
                                                            {isPositiveReturn ? "▲" : "▼"} {expectedReturnStr}
                                                        </span>
                                                        <span className="text-[10px] text-[#5d606b] font-medium tracking-wider uppercase">
                                                            ({row.is_up ? "Bullish" : "Bearish"})
                                                        </span>
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

export default MovementProbability;
