import React, { useState, useMemo } from "react";
import api from "../api/axios";
import Spinner from "./Spinner";

const ClusteringAnalysis = ({ portfolios }) => {
    const [selectedPortfolio, setSelectedPortfolio] = useState("all");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState("");

    // New Feature States
    const [drawOutline, setDrawOutline] = useState(false);
    const [sortOrder, setSortOrder] = useState("default");

    const runAnalysis = async () => {
        setLoading(true);
        setError("");
        setResult(null);

        try {
            const res = await api.get(`/api/analysis/clustering/?portfolio_id=${selectedPortfolio}&draw_outline=${drawOutline}`);
            setResult(res.data);
        } catch (err) {
            setError(err.response?.data?.error || "Error running clustering analysis.");
        } finally {
            setLoading(false);
        }
    };

    // Sort the table data
    const sortedData = useMemo(() => {
        if (!result || !result.table_data) return [];

        let data = [...result.table_data];

        if (sortOrder === "high_risk") {
            data.sort((a, b) => a.cluster_name === "High return – High risk" ? -1 : (b.cluster_name === "High return – High risk" ? 1 : 0));
        } else if (sortOrder === "moderate_risk") {
            data.sort((a, b) => a.cluster_name === "Moderate return – Low risk" ? -1 : (b.cluster_name === "Moderate return – Low risk" ? 1 : 0));
        } else if (sortOrder === "low_return") {
            data.sort((a, b) => a.cluster_name === "Low return – High risk" ? -1 : (b.cluster_name === "Low return – High risk" ? 1 : 0));
        } else {
            // Default "default" - alphabetical sort on Ticker
            data.sort((a, b) => a.ticker.localeCompare(b.ticker));
        }

        return data;

    }, [result, sortOrder]);

    return (
        <div className="h-full flex flex-col">
            <div className="p-4 border-b border-[#2b2b43] bg-[#1e222d] flex flex-col md:flex-row md:items-center justify-between gap-4">
                <h2 className="text-lg font-semibold text-white tracking-wide">Clustering Analysis</h2>

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

                    <label className="flex items-center space-x-2 cursor-pointer group">
                        <input
                            type="checkbox"
                            className="form-checkbox bg-[#131722] border-[#2b2b43] text-[#2962FF] rounded focus:ring-0 cursor-pointer"
                            checked={drawOutline}
                            onChange={(e) => setDrawOutline(e.target.checked)}
                        />
                        <span className="text-sm text-[#787b86] group-hover:text-[#d1d4dc] transition-colors">
                            Draw Outline
                        </span>
                    </label>

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
                            {loading ? "Running..." : "Run Clustering"}
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
                        {/* CHART AREA */}
                        <div className="relative border border-[#2b2b43] bg-[#1e222d] rounded-lg overflow-hidden p-2 flex justify-center shadow-lg">
                            <img
                                src={result.image_url}
                                alt="Clustering plot"
                                className="max-w-full rounded shadow-md border border-[rgba(255,255,255,0.05)] w-full object-contain mix-blend-screen opacity-90"
                                style={{ maxHeight: '400px', filter: 'invert(0.85) hue-rotate(180deg)' }}
                            />
                        </div>

                        {/* TABLE AREA */}
                        <div className="bg-[#1e222d] border border-[#2b2b43] rounded-lg overflow-hidden shadow-lg">
                            <div className="p-3 border-b border-[#2b2b43] flex justify-between items-center bg-[#181c25]">
                                <h3 className="text-sm font-semibold text-white tracking-wide">Cluster Assignments</h3>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-[#787b86]">Sort:</span>
                                    <select
                                        className="bg-[#131722] border border-[#2b2b43] text-[#d1d4dc] text-xs rounded px-2 py-1 focus:outline-none focus:border-[#2962FF]"
                                        value={sortOrder}
                                        onChange={(e) => setSortOrder(e.target.value)}
                                    >
                                        <option value="default">Ticker (A-Z)</option>
                                        <option value="high_risk">🟢 High return – High risk</option>
                                        <option value="moderate_risk">🔵 Mod return – Low risk</option>
                                        <option value="low_return">🔴 Low return – High risk</option>
                                    </select>
                                </div>
                            </div>

                            <div className="overflow-x-auto">
                                <table className="min-w-full text-xs text-left">
                                    <thead className="bg-[#131722] text-[#787b86] uppercase tracking-wider text-[10px]">
                                        <tr>
                                            <th className="px-4 py-2 font-medium">Symbol</th>
                                            <th className="px-4 py-2 font-medium">Avg Return</th>
                                            <th className="px-4 py-2 font-medium">Volatility</th>
                                            <th className="px-4 py-2 font-medium">Sharpe</th>
                                            <th className="px-4 py-2 font-medium">RSI</th>
                                            <th className="px-4 py-2 font-medium">Classification</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-[#2b2b43]">
                                        {sortedData.map((row, idx) => (
                                            <tr key={idx} className="hover:bg-[#2a2e39] transition-colors group">
                                                <td className="px-4 py-3 font-bold text-white group-hover:text-[#2962FF] transition-colors">{row.ticker}</td>
                                                <td className={`px-4 py-3 ${row.avg_return >= 0 ? 'text-[#089981]' : 'text-[#f23645]'}`}>
                                                    {row.avg_return >= 0 ? '+' : ''}{row.avg_return}%
                                                </td>
                                                <td className="px-4 py-3 text-[#d1d4dc]">{row.volatility}%</td>
                                                <td className={`px-4 py-3 ${row.sharpe >= 1 ? 'text-[#089981]' : (row.sharpe < 0 ? 'text-[#f23645]' : 'text-[#d1d4dc]')}`}>
                                                    {row.sharpe}
                                                </td>
                                                <td className="px-4 py-3 text-[#d1d4dc]">{row.rsi}</td>
                                                <td className="px-4 py-3">
                                                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold tracking-wide border
                                                        ${row.cluster_name.includes("High return") ? "bg-[rgba(8,153,129,0.1)] text-[#089981] border-[#089981]/30" : ""}
                                                        ${row.cluster_name.includes("Moderate return") ? "bg-[rgba(41,98,255,0.1)] text-[#2962FF] border-[#2962FF]/30" : ""}
                                                        ${row.cluster_name.includes("Low return") ? "bg-[rgba(242,54,69,0.1)] text-[#f23645] border-[#f23645]/30" : ""}
                                                    `}>
                                                        {row.cluster_name.replace('–', '|')}
                                                    </span>
                                                </td>
                                            </tr>
                                        ))}
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

export default ClusteringAnalysis;
