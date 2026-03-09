import React, { useState, useEffect } from "react";
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
} from "recharts";

// Custom shape for the Candlestick
const CandlestickRender = (props) => {
    const { x, y, width, height, low, high, open, close } = props;

    // Sometimes the Y-Axis passes strings, ensure they are numbers
    const numOpen = Number(open) || 0;
    const numClose = Number(close) || 0;

    const isGrowth = numClose > numOpen;
    const color = isGrowth ? "#16a34a" : "#ef4444"; // Green for up, Red for down

    const halfWidth = width / 2;
    const centerX = x + halfWidth;

    // Calculate Y coordinates for the wicks
    // Recharts Y-axis is inverted (0 is top), so higher prices have lower Y values.
    // However, props.y and props.height already account for the body (Open->Close).
    // We need to use the scales from context, but a simpler hack is rendering rect + line based on the given props if possible, 
    // OR we just use the raw payload and calculate the ratio.
    // Wait, the easiest way is checking the `yAxis` scale function passed via recharts context.

    // Instead of doing manual math without the scale function, let's just use the `payload`
    const payload = props.payload;

    // Fallback if data is malformed
    if (!payload || !payload.Open || !payload.Close || !payload.High || !payload.Low) {
        return <rect x={x} y={y} width={width} height={height} fill="#ccc" />;
    }

    return (
        <g stroke={color} fill={color} strokeWidth="1.5">
            {/* The wick (High to Low) */}
            <path d={`M${centerX},${props.yLow || y} v${(props.yHigh || y) - (props.yLow || y)}`} />

            {/* The body (Open to Close) */}
            <rect
                x={x}
                y={y}
                width={width}
                height={Math.max(height, 1)} // Minimum 1px height so very small changes are visible
                fill={isGrowth ? "transparent" : color} // Hollow green, solid red (classic style)
            />
        </g>
    );
};


const CryptocurrencyAnalysis = () => {
    const [symbolInput, setSymbolInput] = useState("BTC-USD");
    const [activeSymbol, setActiveSymbol] = useState("BTC-USD");
    const [interval, setInterval] = useState("1m");
    const [period, setPeriod] = useState("1d");
    const [isLive, setIsLive] = useState(false);

    const [models, setModels] = useState({
        sma: false,
        ema: false,
        trend: false
    });

    // Search State
    const [searchQuery, setSearchQuery] = useState("");
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);

    const [chartData, setChartData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchCryptoData = async (showLoading = true) => {
        if (showLoading) setLoading(true);
        setError(null);

        try {
            // Build the models array for the API
            const activeModels = Object.keys(models).filter(key => models[key]);

            const response = await api.post(`/api/ml_models/crypto/?t=${new Date().getTime()}`, {
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
            setError("Failed to fetch live market data.");
        } finally {
            if (showLoading) setLoading(false);
        }
    };

    // Fetch on parameters change
    useEffect(() => {
        if (activeSymbol) {
            fetchCryptoData(true);
        }
        // eslint-disable-next-line
    }, [activeSymbol, interval, period, models]);

    // Search Debounce Effect
    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            if (searchQuery.trim()) {
                setIsSearching(true);
                try {
                    const res = await api.get(`/api/stocks/search/?q=${searchQuery}`);
                    setSearchResults(res.data);
                    setShowDropdown(true);
                } catch (e) {
                    console.error(e);
                }
                setIsSearching(false);
            } else {
                setSearchResults([]);
                setShowDropdown(false);
            }
        }, 500);

        return () => clearTimeout(delayDebounceFn);
    }, [searchQuery]);

    // Live polling when isLive is true
    useEffect(() => {
        let intervalId;
        if (isLive) {
            intervalId = window.setInterval(() => {
                fetchCryptoData(false);
            }, 10000);
        }
        return () => {
            if (intervalId) window.clearInterval(intervalId);
        };
        // eslint-disable-next-line
    }, [isLive, activeSymbol, interval, period, models]);

    const handleAnalyze = () => {
        if (searchQuery.trim()) {
            setActiveSymbol(searchQuery);
            setShowDropdown(false);
        }
    };

    const handleSelectStock = (stock) => {
        setSearchQuery(stock.ticker);
        setActiveSymbol(stock.ticker);
        setSearchResults([]);
        setShowDropdown(false);
    };

    // Handle Checkbox Changes
    const handleModelChange = (modelName) => {
        setModels(prev => ({ ...prev, [modelName]: !prev[modelName] }));
    };

    // Data formatting for Recharts ComposedChart
    // The "Bar" series will be used for the candlestick. We need to trick Recharts into
    // making the Bar bounds match Open/Close. 
    const formattedData = chartData.map(d => {
        const minBody = Math.min(d.Open, d.Close);
        const maxBody = Math.max(d.Open, d.Close);

        let dateStr = d.Date;
        if (d.Date && d.Date.includes(" ")) {
            if (interval === '1m' || interval === '1h') {
                const parts = d.Date.split(" ");
                const datePart = parts[0].substring(5); // MM-DD
                const timePart = parts[1].substring(0, 5); // HH:MM
                dateStr = `${datePart} ${timePart}`;
            } else {
                dateStr = d.Date.split(" ")[0]; // YYYY-MM-DD
            }
        }

        return {
            ...d,
            CleanDate: dateStr,
            CandleBounds: [minBody, maxBody],
        };
    });

    // If interval is 1m, only show the last 30 candles
    let displayData = formattedData;
    if (interval === '1m' && formattedData.length > 30) {
        displayData = formattedData.slice(-30);
    }

    // Determine Y-Axis Domain dynamically so chart isn't squished to 0
    let minPrice = 'auto';
    let maxPrice = 'auto';
    if (displayData.length > 0) {
        const lows = displayData.map(d => d.Low).filter(v => v != null);
        const highs = displayData.map(d => d.High).filter(v => v != null);
        if (lows.length > 0 && highs.length > 0) {
            // Tighten the padding for extremely small intraday movements so candlesticks appear large
            const minL = Math.min(...lows);
            const maxH = Math.max(...highs);
            const range = maxH - minL;

            // Add a very small padding (0.1%) based on the range itself, not absolute price (which caused huge 5% gaps for BTC)
            const padding = range * 0.1 > 0 ? range * 0.1 : minL * 0.001;
            minPrice = minL - padding;
            maxPrice = maxH + padding;
        }
    }

    // Custom Tooltip for Candlestick
    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            const dataPoint = payload[0].payload;
            return (
                <div className="bg-[#1e222d] border border-[#2b2b43] p-3 rounded text-white shadow-xl text-xs">
                    <p className="font-bold text-[#d1d4dc] mb-2">{dataPoint.Date}</p>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                        <span className="text-gray-400">Open:</span>
                        <span className="font-mono">${Number(dataPoint.Open).toFixed(2)}</span>
                        <span className="text-gray-400">High:</span>
                        <span className="font-mono text-green-400">${Number(dataPoint.High).toFixed(2)}</span>
                        <span className="text-gray-400">Low:</span>
                        <span className="font-mono text-red-400">${Number(dataPoint.Low).toFixed(2)}</span>
                        <span className="text-gray-400">Close:</span>
                        <span className="font-mono">${Number(dataPoint.Close).toFixed(2)}</span>
                    </div>
                </div>
            );
        }
        return null;
    };

    return (
        <div className="bg-[#1e222d] text-white p-6 shadow-xl rounded-lg border border-[#2b2b43]">

            {/* Control Panel */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">

                {/* Search Input Area */}
                <div className="flex items-center space-x-2 relative w-64 z-50">
                    <div className="bg-[#131722] border border-[#2b2b43] rounded px-3 py-1.5 focus-within:border-[#2962FF] transition-colors w-full flex items-center">
                        <input
                            className="bg-transparent text-sm text-[#d1d4dc] outline-none uppercase font-bold w-full"
                            type="text"
                            value={searchQuery}
                            onChange={(e) => {
                                setSearchQuery(e.target.value);
                                setShowDropdown(true);
                            }}
                            onFocus={() => {
                                if (searchResults.length > 0) setShowDropdown(true);
                            }}
                            placeholder="Search TICKER..."
                            onKeyDown={(e) => e.key === 'Enter' && handleAnalyze()}
                        />
                    </div>
                    <button
                        onClick={handleAnalyze}
                        className="bg-[#2962FF] hover:bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium transition-colors hover:shadow-[0_0_10px_rgba(41,98,255,0.5)]"
                    >
                        Analyze
                    </button>

                    {/* Autocomplete Dropdown */}
                    {showDropdown && searchResults.length > 0 && (
                        <div className="absolute top-10 left-0 w-full bg-[#1e222d] border border-[#2b2b43] rounded shadow-2xl max-h-60 overflow-y-auto">
                            {searchResults.map((result, idx) => (
                                <div
                                    key={idx}
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
                <button
                    onClick={() => setIsLive(!isLive)}
                    className={`px-4 py-1.5 rounded text-sm font-medium flex items-center gap-2 transition-colors ${isLive
                        ? 'bg-red-500 hover:bg-red-600 text-white shadow-[0_0_10px_rgba(239,68,68,0.5)]'
                        : 'bg-green-600 hover:bg-green-700 text-white shadow-[0_0_10px_rgba(22,163,74,0.5)]'
                        }`}
                >
                    {isLive && <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>}
                    {isLive ? 'Stop Live' : 'Live'}
                </button>
            </div>

            <div className="flex bg-[#131722] border border-[#2b2b43] rounded overflow-hidden">
                {[{ l: '1m', p: '1d' }, { l: '1h', p: '5d' }, { l: '1d', p: '6mo' }, { l: '1wk', p: '2y' }].map(tf => (
                    <button
                        key={tf.l}
                        onClick={() => { setInterval(tf.l); setPeriod(tf.p); }}
                        className={`px-3 py-1.5 text-xs font-semibold flex items-center gap-1 ${interval === tf.l ? 'bg-[#2b2b43] text-white' : 'text-[#787b86] hover:bg-[#1e222d]'}`}
                    >
                        {interval === tf.l && tf.l === '1m' && <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>}
                        {tf.l}
                    </button>
                ))}
            </div>

            <div className="flex items-center space-x-4 bg-[#131722] p-2 rounded border border-[#2b2b43]">
                <h4 className="text-xs text-[#787b86] uppercase font-bold mr-2">Models:</h4>

                <label className="flex items-center space-x-1.5 cursor-pointer text-sm">
                    <input type="checkbox" checked={models.sma} onChange={() => handleModelChange('sma')} className="accent-blue-500" />
                    <span>SMA</span>
                </label>

                <label className="flex items-center space-x-1.5 cursor-pointer text-sm">
                    <input type="checkbox" checked={models.ema} onChange={() => handleModelChange('ema')} className="accent-purple-500" />
                    <span>EMA</span>
                </label>

                <label className="flex items-center space-x-1.5 cursor-pointer text-sm">
                    <input type="checkbox" checked={models.trend} onChange={() => handleModelChange('trend')} className="accent-yellow-500" />
                    <span>Trend</span>
                </label>
            </div>

            {/* Error Message */}
            {
                error && (
                    <div className="bg-red-500/10 border border-red-500/50 text-red-400 p-3 rounded mb-6 text-sm">
                        {error}
                    </div>
                )
            }

            {/* Chart Area */}
            <div className="w-full h-[700px] relative mt-4">
                {loading && (
                    <div className="absolute inset-0 bg-[#1e222d]/80 z-10 flex items-center justify-center rounded">
                        <Spinner />
                    </div>
                )}

                {!loading && chartData.length > 0 && (
                    <ResponsiveContainer width="100%" height="100%">
                        <ComposedChart data={displayData} margin={{ top: 10, right: 10, left: 10, bottom: 20 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2b2b43" vertical={false} />

                            <XAxis
                                dataKey="CleanDate"
                                stroke="#787b86"
                                tick={{ fill: '#787b86', fontSize: 12 }}
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

                            {/* Time Series Modles (Lines) */}
                            {models.sma && (
                                <Line type="monotone" dataKey="SMA" stroke="#3b82f6" strokeWidth={2} dot={false} animateNewValues={false} isAnimationActive={false} />
                            )}
                            {models.ema && (
                                <Line type="monotone" dataKey="EMA" stroke="#a855f7" strokeWidth={2} dot={false} animateNewValues={false} isAnimationActive={false} />
                            )}
                            {models.trend && (
                                <Line type="linear" dataKey="Trend" stroke="#eab308" strokeWidth={2} strokeDasharray="5 5" dot={false} animateNewValues={false} isAnimationActive={false} />
                            )}

                            {/* Candlestick (Bar using custom shape) */}
                            {/* We pass Open, Close, High, Low dynamically inside the payload, but shape needs to draw the wick. 
                                Since Bar chart maps 'Y' to the array bounds, making the wick exact requires a little scale math. 
                                Recharts standard Bar bounds don't expose High/Low inherently to the custom shape's Y axis pixels unless we compute it. 
                                For a true robust candlestick in Recharts without extreme custom math, we just use standard Bars for body and 
                                ErrorBars or layered lines for wicks, OR we rely on a simplified View. 
                                For now, we will render the Body using Bar dataKey=CandleBounds. */}
                            <Bar
                                dataKey="CandleBounds"
                                name="Price (O/H/L/C)"
                                fill="#16a34a"
                                isAnimationActive={false}
                                shape={(props) => {
                                    const { x, y, width, height, payload } = props;

                                    // For exact Y pixels of High and Low, we must access the YAxis scale function.
                                    // It is sometimes passed in `yAxis` property, let's try safely.
                                    // If not available, we mathematically infer it from the body.
                                    const scale = props.yAxis && props.yAxis.scale;

                                    let yHigh = y;
                                    let yLow = y + height;

                                    if (scale && typeof scale === 'function') {
                                        // Recharts Y-axis is inverted (0 is top)
                                        yHigh = scale(payload.High);
                                        yLow = scale(payload.Low);
                                    }

                                    return <CandlestickRender {...props} yHigh={yHigh} yLow={yLow} open={payload.Open} close={payload.Close} high={payload.High} low={payload.Low} />;
                                }}
                            />
                        </ComposedChart>
                    </ResponsiveContainer>
                )}

                {!loading && chartData.length === 0 && !error && (
                    <div className="absolute inset-0 flex items-center justify-center text-gray-500">
                        No data available. Try a different symbol or timeframe.
                    </div>
                )}
            </div>
        </div>
    );
};

export default CryptocurrencyAnalysis;
