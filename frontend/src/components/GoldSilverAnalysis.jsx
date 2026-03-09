import React, { useState, useEffect } from "react";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ScatterChart,
    Scatter,
    ResponsiveContainer,
    BarChart,
    Bar,
    Cell,
} from "recharts";
import api from "../api/axios";
import Spinner from "./Spinner";

const GoldSilverAnalysis = () => {
    const [data, setData] = useState({ historical: [], predictions: [] });
    const [loading, setLoading] = useState(true);
    const [activeView, setActiveView] = useState("gold"); // "gold", "silver", "correlation"
    const [isOpen, setIsOpen] = useState(false);

    const [interval, setInterval] = useState("1y"); // '1d', '1mo', '3mo', '1y'

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // Post to backend with selected interval
                const response = await api.post("/api/ml_models/gold-silver/", { interval });
                setData(response.data);
            } catch (error) {
                console.error("Error fetching Gold/Silver data", error);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [interval]);

    if (loading) return (
        <div className="bg-white p-6 shadow rounded mb-8 min-h-[500px] flex items-center justify-center">
            <Spinner />
        </div>
    );

    // Combine historical and predictions for Line Charts
    const combinedDataSeries = [...data.historical, ...data.predictions].sort((a, b) => {
        // Sort by TimeIndex or Year depending on what is returned to ensure order
        return new Date(a.Date) - new Date(b.Date);
    });

    const renderChart = () => {
        switch (activeView) {
            case "gold":
                return (
                    <ResponsiveContainer width="100%" height={400}>
                        <LineChart data={combinedDataSeries} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey={interval === '1y' ? "Year" : "Date"} />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line type="monotone" dataKey="Actual_GLD" stroke="#facc15" strokeWidth={2} dot={interval === '1y'} name="Actual GLD" connectNulls />
                            <Line type="monotone" dataKey="Predicted_GLD" stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" dot={interval === '1y'} name="Predicted GLD" connectNulls />
                        </LineChart>
                    </ResponsiveContainer>
                );
            case "silver":
                return (
                    <ResponsiveContainer width="100%" height={400}>
                        <LineChart data={combinedDataSeries} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey={interval === '1y' ? "Year" : "Date"} />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Line type="monotone" dataKey="Actual_SLV" stroke="#94a3b8" strokeWidth={2} dot={interval === '1y'} name="Actual SLV" connectNulls />
                            <Line type="monotone" dataKey="Predicted_SLV" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 5" dot={interval === '1y'} name="Predicted SLV" connectNulls />
                        </LineChart>
                    </ResponsiveContainer>
                );
            case "correlation":
                // Format data for scatter
                const scatterHist = data.historical.map(d => ({ x: d.Actual_SLV, y: d.Actual_GLD, Year: d.Year }));
                const scatterPred = data.predictions.map(d => ({ x: d.Predicted_SLV, y: d.Predicted_GLD, Year: d.Year }));

                return (
                    <ResponsiveContainer width="100%" height={400}>
                        <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis type="number" dataKey="x" name="Silver (SLV)" unit="$" />
                            <YAxis type="number" dataKey="y" name="Gold (GLD)" unit="$" />
                            <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                            <Legend />
                            <Scatter name="Historical (Actual)" data={scatterHist} fill="#9333ea" opacity={0.7} />
                            <Scatter name="Predicted (Next 10 Yrs)" data={scatterPred} fill="#16a34a" shape="cross" />
                        </ScatterChart>
                    </ResponsiveContainer>
                );
            case "shap":
                const shapData = data.explanations?.shap?.features?.map((feature, idx) => ({
                    name: feature,
                    Gold_Impact: data.explanations.shap.gld_importance[idx] || 0,
                    Silver_Impact: data.explanations.shap.slv_importance[idx] || 0
                })) || [];

                return (
                    <div className="bg-white p-4 rounded border border-gray-200">
                        <h3 className="text-lg font-bold mb-4">SHAP Feature Importance (Global)</h3>
                        <p className="text-gray-600 mb-6 text-sm">
                            SHAP values show the average absolute impact of each feature on the model's predictions.
                            Our multi-variable model looks at historical lags to understand price momentum.
                        </p>
                        <ResponsiveContainer width="100%" height={400}>
                            <BarChart data={shapData} layout="vertical" margin={{ top: 20, right: 30, left: 150, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis type="number" />
                                <YAxis dataKey="name" type="category" />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="Gold_Impact" fill="#facc15" name="Gold Absolute Impact" />
                                <Bar dataKey="Silver_Impact" fill="#94a3b8" name="Silver Absolute Impact" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                );
            case "lime":
                const yearExplained = data.explanations?.lime?.explained_instance_year;
                const limeGldData = data.explanations?.lime?.gld_explanation?.map(([feature, weight]) => ({
                    name: feature,
                    Weight: weight
                })) || [];

                const limeSlvData = data.explanations?.lime?.slv_explanation?.map(([feature, weight]) => ({
                    name: feature,
                    Weight: weight
                })) || [];

                return (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-white p-4 rounded border border-gray-200">
                            <h3 className="text-lg font-bold mb-2">LIME Explanation: Gold ({yearExplained})</h3>
                            <p className="text-gray-600 mb-4 text-sm">Local decision boundaries explaining the prediction for year {yearExplained}.</p>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={limeGldData} layout="vertical" margin={{ top: 5, right: 30, left: 150, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis type="number" />
                                    <YAxis dataKey="name" type="category" width={100} />
                                    <Tooltip />
                                    <Bar dataKey="Weight" name="Feature Weight">
                                        {limeGldData.map((entry, index) => (
                                            <Cell key={`cell-gld-${index}`} fill={entry.Weight > 0 ? '#22c55e' : '#ef4444'} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="bg-white p-4 rounded border border-gray-200">
                            <h3 className="text-lg font-bold mb-2">LIME Explanation: Silver ({yearExplained})</h3>
                            <p className="text-gray-600 mb-4 text-sm">Local decision boundaries explaining the prediction for year {yearExplained}.</p>
                            <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={limeSlvData} layout="vertical" margin={{ top: 5, right: 30, left: 150, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis type="number" />
                                    <YAxis dataKey="name" type="category" width={100} />
                                    <Tooltip />
                                    <Bar dataKey="Weight" name="Feature Weight">
                                        {limeSlvData.map((entry, index) => (
                                            <Cell key={`cell-slv-${index}`} fill={entry.Weight > 0 ? '#22c55e' : '#ef4444'} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className="bg-white text-gray-900 p-6 shadow rounded mb-8">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold">Gold and Silver Correlation Analysis (Multivariate)</h2>
                <div className="flex items-center space-x-4">
                    {/* Timeframe Selectors */}
                    {isOpen && (
                        <div className="flex bg-gray-100 rounded border border-gray-300 overflow-hidden text-sm">
                            {[{ l: '1D', v: '1d' }, { l: '1M', v: '1mo' }, { l: '3M', v: '3mo' }, { l: '1Y', v: '1y' }].map(td => (
                                <button
                                    key={td.v}
                                    onClick={() => setInterval(td.v)}
                                    className={`px-3 py-1 font-semibold transition-colors ${interval === td.v ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-200'}`}
                                >
                                    {td.l}
                                </button>
                            ))}
                        </div>
                    )}
                    <button
                        onClick={() => setIsOpen(!isOpen)}
                        className="bg-gray-800 text-white px-3 py-1.5 rounded text-sm hover:bg-gray-700 transition"
                    >
                        {isOpen ? "Hide Analysis" : "Show Analysis"}
                    </button>
                </div>
            </div>

            {isOpen && (
                <>
                    <div className="flex gap-4 mb-6">
                        <button
                            className={`px-4 py-2 rounded font-semibold ${activeView === "gold" ? "bg-yellow-500 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
                            onClick={() => setActiveView("gold")}
                        >
                            Gold Prediction
                        </button>
                        <button
                            className={`px-4 py-2 rounded font-semibold ${activeView === "silver" ? "bg-slate-400 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
                            onClick={() => setActiveView("silver")}
                        >
                            Silver Prediction
                        </button>
                        <button
                            className={`px-4 py-2 rounded font-semibold ${activeView === "correlation" ? "bg-purple-600 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
                            onClick={() => setActiveView("correlation")}
                        >
                            Gold Silver Co-relation
                        </button>
                        <button
                            className={`px-4 py-2 rounded font-semibold ${activeView === "shap" ? "bg-pink-500 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
                            onClick={() => setActiveView("shap")}
                        >
                            SHAP Explainability
                        </button>
                        <button
                            className={`px-4 py-2 rounded font-semibold ${activeView === "lime" ? "bg-emerald-500 text-white" : "bg-gray-200 text-gray-700 hover:bg-gray-300"}`}
                            onClick={() => setActiveView("lime")}
                        >
                            LIME Explainability
                        </button>
                    </div>

                    <div className="mb-8">
                        {renderChart()}
                    </div>

                    <div className="overflow-x-auto">
                        <h3 className="text-lg font-bold mb-4">Historical & Predicted Prices</h3>
                        <table className="min-w-full text-sm border">
                            <thead className="bg-gray-100">
                                <tr>
                                    <th className="text-left p-3 border">Year</th>
                                    <th className="text-left p-3 border">Actual GLD</th>
                                    <th className="text-left p-3 border">Predicted GLD</th>
                                    <th className="text-left p-3 border">Actual SLV</th>
                                    <th className="text-left p-3 border">Predicted SLV</th>
                                </tr>
                            </thead>
                            <tbody>
                                {combinedDataSeries.map((row, index) => (
                                    <tr key={index} className="hover:bg-gray-50 border-b">
                                        <td className="p-3 border font-semibold">{row.Year}</td>
                                        <td className="p-3 border">{row.Actual_GLD || "-"}</td>
                                        <td className="p-3 border text-gray-600 italic">{row.Predicted_GLD || "-"}</td>
                                        <td className="p-3 border">{row.Actual_SLV || "-"}</td>
                                        <td className="p-3 border text-gray-600 italic">{row.Predicted_SLV || "-"}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    );
};

export default GoldSilverAnalysis;
