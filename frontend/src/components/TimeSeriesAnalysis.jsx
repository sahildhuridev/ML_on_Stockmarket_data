import React, { useState, useEffect, useCallback } from "react";
import api from "../api/axios";
import Spinner from "./Spinner";
import {
    ComposedChart,
    Line,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Brush,
    ReferenceArea,
} from "recharts";

// Custom Candlestick Render
const CandlestickRender = (props) => {
    const { x, y, width, height, payload } = props;

    if (!payload || payload.Open == null || payload.Close == null || payload.High == null || payload.Low == null) {
        return null; // Skip rendering candlestick for future predicted dates
    }

    const numOpen = Number(payload.Open);
    const numClose = Number(payload.Close);

    const isGrowth = numClose > numOpen;
    const color = isGrowth ? "#16a34a" : "#ef4444";

    const centerX = x + width / 2;

    const scale = props.yAxis && props.yAxis.scale;
    let yHigh = y;
    let yLow = y + height;

    if (scale && typeof scale === 'function') {
        yHigh = scale(payload.High);
        yLow = scale(payload.Low);
    }

    return (
        <g stroke={color} fill={color} strokeWidth="1.5">
            <path d={`M${centerX},${yLow} v${yHigh - yLow}`} />
            <rect
                x={x}
                y={y}
                width={width}
                height={Math.max(height, 1)}
                fill={isGrowth ? "transparent" : color}
            />
        </g>
    );
};

const TimeSeriesAnalysis = () => {
    const [isCollapsed, setIsCollapsed] = useState(false);
    const [symbolInput, setSymbolInput] = useState("AAPL");
    const [activeSymbol, setActiveSymbol] = useState("AAPL");
    const [searchResults, setSearchResults] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [interval, setInterval] = useState("1d");
    const [period, setPeriod] = useState("1y");

    const [models, setModels] = useState({
        arima: false,
        linear: false,
        sma_extrapolate: false,
        poly: false
    });

    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Zoom state for click-drag zoom
    const [refAreaLeft, setRefAreaLeft] = useState(null);
    const [refAreaRight, setRefAreaRight] = useState(null);
    const [zoomLeft, setZoomLeft] = useState(null);
    const [zoomRight, setZoomRight] = useState(null);
    const isZoomed = zoomLeft !== null && zoomRight !== null;

    const fetchAnalysisData = async () => {
        setLoading(true);
        setError(null);

        try {
            const activeModels = Object.keys(models).filter(key => models[key]);

            const response = await api.post("/api/ml_models/time-series/", {
                symbol: activeSymbol,
                interval: interval,
                period: period,
                models: activeModels
            });

            if (response.data.error) {
                setError(response.data.error);
                setChartData([]);
            } else {
                setChartData(response.data.data);
            }
        } catch (err) {
            console.error(err);
            setError("Failed to fetch time series predictions.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAnalysisData();
        // eslint-disable-next-line
    }, [activeSymbol, interval, period, models]);

    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            const q = symbolInput.trim();
            if (q.length > 0) {
                try {
                    const res = await api.get(`/api/stocks/search/?q=${q}`);
                    setSearchResults(res.data || []);
                    setShowDropdown(true);
                } catch (e) {
                    setSearchResults([]);
                }
            } else {
                setSearchResults([]);
                setShowDropdown(false);
            }
        }, 350);

        return () => clearTimeout(delayDebounceFn);
    }, [symbolInput]);

    const handleAnalyze = () => {
        const next = symbolInput.trim().toUpperCase();
        if (!next) return;
        setActiveSymbol(next);
        setShowDropdown(false);
    };

    const handleModelChange = (modelName) => {
        setModels(prev => ({ ...prev, [modelName]: !prev[modelName] }));
    };

    const handleSelectStock = (stock) => {
        const ticker = (stock?.ticker || "").toUpperCase();
        if (!ticker) return;
        setSymbolInput(ticker);
        setActiveSymbol(ticker);
        setSearchResults([]);
        setShowDropdown(false);
    };

    // Format Data (must be before zoom handlers that reference it)
    const formattedData = chartData.map(d => {
        const hasBody = d.Open != null && d.Close != null;
        const minBody = hasBody ? Math.min(d.Open, d.Close) : null;
        const maxBody = hasBody ? Math.max(d.Open, d.Close) : null;

        const dateStr = d.Date && d.Date.includes(" ") ? d.Date.split(" ")[0] : d.Date;

        return {
            ...d,
            CleanDate: dateStr,
            CandleBounds: hasBody ? [minBody, maxBody] : [0, 0],
        };
    });

    // --- Zoom handlers ---
    const handleMouseDown = useCallback((e) => {
        if (e && e.activeLabel) setRefAreaLeft(e.activeLabel);
    }, []);

    const handleMouseMove = useCallback((e) => {
        if (refAreaLeft && e && e.activeLabel) setRefAreaRight(e.activeLabel);
    }, [refAreaLeft]);

    const handleMouseUp = useCallback(() => {
        if (!refAreaLeft || !refAreaRight) {
            setRefAreaLeft(null);
            setRefAreaRight(null);
            return;
        }
        // Determine indices for left & right in formattedData
        const allDates = formattedData.map(d => d.CleanDate);
        let idxL = allDates.indexOf(refAreaLeft);
        let idxR = allDates.indexOf(refAreaRight);
        if (idxL > idxR) [idxL, idxR] = [idxR, idxL];

        if (idxR - idxL >= 1) {
            setZoomLeft(idxL);
            setZoomRight(idxR);
        }
        setRefAreaLeft(null);
        setRefAreaRight(null);
    }, [refAreaLeft, refAreaRight, formattedData]);

    const resetZoom = useCallback(() => {
        setZoomLeft(null);
        setZoomRight(null);
    }, []);

    // Sliced data for zoom view
    const displayData = isZoomed
        ? formattedData.slice(zoomLeft, zoomRight + 1)
        : formattedData;

    // Dynamic Y-Axis scale based on visible (possibly zoomed) data
    let minPrice = 'auto';
    let maxPrice = 'auto';
    if (displayData.length > 0) {
        const allPrices = [];
        displayData.forEach(d => {
            if (d.Low != null) allPrices.push(d.Low);
            if (d.High != null) allPrices.push(d.High);
            if (d.LR_Predict != null) allPrices.push(d.LR_Predict);
            if (d.ARIMA_Predict != null) allPrices.push(d.ARIMA_Predict);
            if (d.SMA_Predict != null) allPrices.push(d.SMA_Predict);
            if (d.Poly_Predict != null) allPrices.push(d.Poly_Predict);
        });

        if (allPrices.length > 0) {
            const minL = Math.min(...allPrices);
            const maxH = Math.max(...allPrices);
            const range = maxH - minL;

            // Add a very small padding (0.1%) based on the range itself
            const padding = range * 0.1 > 0 ? range * 0.1 : minL * 0.001;
            minPrice = minL - padding;
            maxPrice = maxH + padding;
        }
    }

    const CustomTooltip = ({ active, payload }) => {
        if (active && payload && payload.length) {
            const dataPoint = payload[0].payload;
            return (
                <div className="bg-[#1e222d] border border-[#2b2b43] p-3 rounded text-white shadow-xl text-xs z-50">
                    <p className="font-bold text-[#d1d4dc] mb-2">{dataPoint.Date}</p>

                    {dataPoint.Open != null ? (
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mb-2 border-b border-[#2b2b43] pb-2">
                            <span className="text-gray-400">Open:</span>
                            <span className="font-mono">${Number(dataPoint.Open).toFixed(2)}</span>
                            <span className="text-gray-400">High:</span>
                            <span className="font-mono text-green-400">${Number(dataPoint.High).toFixed(2)}</span>
                            <span className="text-gray-400">Low:</span>
                            <span className="font-mono text-red-400">${Number(dataPoint.Low).toFixed(2)}</span>
                            <span className="text-gray-400">Close:</span>
                            <span className="font-mono">${Number(dataPoint.Close).toFixed(2)}</span>
                        </div>
                    ) : (
                        <p className="italic text-yellow-500 mb-2 border-b border-[#2b2b43] pb-2">Future Prediction</p>
                    )}

                    <div className="space-y-1 mt-2">
                        {dataPoint.LR_Predict != null && (
                            <p className="text-blue-400"><span className="text-gray-400">LR Trend:</span> ${Number(dataPoint.LR_Predict).toFixed(2)}</p>
                        )}
                        {dataPoint.ARIMA_Predict != null && (
                            <p className="text-amber-300"><span className="text-gray-400">ARIMA Forecast:</span> ${Number(dataPoint.ARIMA_Predict).toFixed(2)}</p>
                        )}
                        {dataPoint.SMA_Predict != null && (
                            <p className="text-emerald-400"><span className="text-gray-400">SMA Extrapolate:</span> ${Number(dataPoint.SMA_Predict).toFixed(2)}</p>
                        )}
                        {dataPoint.Poly_Predict != null && (
                            <p className="text-pink-400"><span className="text-gray-400">Poly Curve:</span> ${Number(dataPoint.Poly_Predict).toFixed(2)}</p>
                        )}
                    </div>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="bg-[#1e222d] text-white p-6 shadow-xl rounded-lg border border-[#2b2b43] mt-6">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold">Price Analysis by Time Series Model (15 Periods Ahead)</h2>
                <button
                    onClick={() => setIsCollapsed(prev => !prev)}
                    className="text-xs font-semibold px-3 py-1.5 rounded border border-[#2b2b43] bg-[#131722] text-[#d1d4dc] hover:bg-[#2a2e39] transition-colors"
                >
                    {isCollapsed ? "Show Analysis" : "Hide Analysis"}
                </button>
            </div>

            {isCollapsed ? null : (
                <>

                    {/* Control Panel */}
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">

                        <div className="flex items-center space-x-2 relative w-72 z-20">
                            <div className="bg-[#131722] border border-[#2b2b43] rounded px-3 py-1.5 focus-within:border-[#2962FF] transition-colors w-full">
                                <input
                                    className="bg-transparent text-sm text-white outline-none uppercase font-bold w-full"
                                    type="text"
                                    value={symbolInput}
                                    onChange={(e) => {
                                        setSymbolInput(e.target.value);
                                        setShowDropdown(true);
                                    }}
                                    onFocus={() => {
                                        if (searchResults.length > 0) setShowDropdown(true);
                                    }}
                                    placeholder="e.g. AAPL"
                                    onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                                />
                            </div>
                            <button
                                onClick={handleAnalyze}
                                className="bg-[#2962FF] hover:bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium transition-colors"
                            >
                                Forecast
                            </button>

                            {showDropdown && searchResults.length > 0 && (
                                <div className="absolute top-10 left-0 w-full bg-[#1e222d] border border-[#2b2b43] rounded shadow-2xl max-h-60 overflow-y-auto">
                                    {searchResults.map((result, idx) => (
                                        <div
                                            key={`${result.ticker}-${idx}`}
                                            className="px-4 py-2 hover:bg-[#2a2e39] cursor-pointer flex justify-between items-center border-b border-[#2b2b43] last:border-b-0"
                                            onClick={() => handleSelectStock(result)}
                                        >
                                            <span className="font-medium text-white truncate max-w-[70%]">{result.company_name}</span>
                                            <span className="text-xs text-[#787b86] font-bold">{result.ticker}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="flex bg-[#131722] border border-[#2b2b43] rounded overflow-hidden">
                            {[
                                { l: '1h', p: '5d' },
                                { l: '1d', p: '1y' },
                                { l: '1wk', p: '2y' },
                                { l: '1mo', p: '5y' }
                            ].map(tf => (
                                <button
                                    key={tf.l}
                                    onClick={() => { setInterval(tf.l); setPeriod(tf.p); }}
                                    className={`px-3 py-1.5 text-xs font-semibold ${interval === tf.l ? 'bg-[#2b2b43] text-white' : 'text-[#787b86] hover:bg-[#1e222d]'}`}
                                >
                                    {tf.l}
                                </button>
                            ))}
                        </div>

                        <div className="flex items-center space-x-4 bg-[#131722] p-2 rounded border border-[#2b2b43]">
                            <h4 className="text-xs text-[#787b86] uppercase font-bold mr-2">Models:</h4>

                            <label className="flex items-center space-x-1.5 cursor-pointer text-sm">
                                <input type="checkbox" checked={models.arima} onChange={() => handleModelChange('arima')} className="accent-amber-400" />
                                <span>ARIMA</span>
                            </label>

                            <label className="flex items-center space-x-1.5 cursor-pointer text-sm">
                                <input type="checkbox" checked={models.linear} onChange={() => handleModelChange('linear')} className="accent-blue-500" />
                                <span>Linear</span>
                            </label>

                            <label className="flex items-center space-x-1.5 cursor-pointer text-sm">
                                <input type="checkbox" checked={models.sma_extrapolate} onChange={() => handleModelChange('sma_extrapolate')} className="accent-emerald-500" />
                                <span>SMA</span>
                            </label>

                            <label className="flex items-center space-x-1.5 cursor-pointer text-sm">
                                <input type="checkbox" checked={models.poly} onChange={() => handleModelChange('poly')} className="accent-pink-500" />
                                <span>Polynomial</span>
                            </label>
                        </div>
                    </div>

                    {error && (
                        <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded mb-6 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Zoom Reset Button */}
                    {isZoomed && (
                        <div className="flex justify-end mb-2">
                            <button
                                onClick={resetZoom}
                                className="text-xs font-semibold px-3 py-1.5 rounded border border-amber-500/40 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 transition-colors"
                            >
                                ⟳ Reset Zoom
                            </button>
                        </div>
                    )}

                    {/* Chart Area */}
                    <div className="w-full h-[550px] relative mt-4">
                        {loading && (
                            <div className="absolute inset-0 bg-[#1e222d]/80 z-10 flex items-center justify-center rounded">
                                <Spinner />
                            </div>
                        )}

                        {!loading && chartData.length > 0 && (
                            <ResponsiveContainer width="100%" height="100%">
                                <ComposedChart
                                    data={displayData}
                                    margin={{ top: 10, right: 10, left: 10, bottom: 40 }}
                                    onMouseDown={handleMouseDown}
                                    onMouseMove={handleMouseMove}
                                    onMouseUp={handleMouseUp}
                                >
                                    <CartesianGrid strokeDasharray="3 3" stroke="#2b2b43" vertical={false} />

                                    <XAxis
                                        dataKey="CleanDate"
                                        stroke="#787b86"
                                        tick={{ fill: '#787b86', fontSize: 11 }}
                                        tickMargin={10}
                                        minTickGap={30}
                                    />

                                    <YAxis
                                        domain={[minPrice, maxPrice]}
                                        orientation="right"
                                        stroke="#787b86"
                                        tick={{ fill: '#787b86', fontSize: 12 }}
                                        tickFormatter={(val) => `$${val.toLocaleString()}`}
                                    />

                                    <Tooltip content={<CustomTooltip />} />
                                    <Legend verticalAlign="top" height={36} iconType="plainline" />

                                    {/* Predictions */}
                                    {models.arima && (
                                        <Line type="monotone" dataKey="ARIMA_Predict" name="ARIMA Forecast" stroke="#f59e0b" strokeWidth={3} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                                    )}
                                    {models.linear && (
                                        <Line type="monotone" dataKey="LR_Predict" name="Linear Extrapolate" stroke="#60a5fa" strokeWidth={3} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                                    )}
                                    {models.sma_extrapolate && (
                                        <Line type="monotone" dataKey="SMA_Predict" name="SMA Project" stroke="#34d399" strokeWidth={3} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                                    )}
                                    {models.poly && (
                                        <Line type="monotone" dataKey="Poly_Predict" name="Poly Curve" stroke="#f472b6" strokeWidth={3} strokeDasharray="4 4" dot={false} isAnimationActive={false} />
                                    )}

                                    {/* Historical Body bounds mapped to custom Candlestick Shape */}
                                    <Bar
                                        dataKey="CandleBounds"
                                        name="Historical (O/H/L/C)"
                                        fill="#787b86"
                                        isAnimationActive={false}
                                        shape={<CandlestickRender />}
                                    />

                                    {/* Brush for zoom/scroll */}
                                    {!isZoomed && (
                                        <Brush
                                            dataKey="CleanDate"
                                            height={28}
                                            stroke="#2962FF"
                                            fill="#131722"
                                            tickFormatter={() => ''}
                                        />
                                    )}

                                    {/* Click-drag selection highlight */}
                                    {refAreaLeft && refAreaRight && (
                                        <ReferenceArea
                                            x1={refAreaLeft}
                                            x2={refAreaRight}
                                            strokeOpacity={0.3}
                                            fill="#2962FF"
                                            fillOpacity={0.15}
                                        />
                                    )}
                                </ComposedChart>
                            </ResponsiveContainer>
                        )}

                        {!loading && chartData.length === 0 && !error && (
                            <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                                No data available. Try a different symbol.
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
};

export default TimeSeriesAnalysis;
