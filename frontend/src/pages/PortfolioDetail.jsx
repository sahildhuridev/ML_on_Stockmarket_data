import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "../api/axios";
import Spinner from "../components/Spinner";

const PortfolioDetail = () => {
  const { id } = useParams();

  const [stocks, setStocks] = useState([]);
  const [loading, setLoading] = useState(false);

  // Search State
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);

  // PE Analysis States
  const [peData, setPeData] = useState(null);
  const [peLoading, setPeLoading] = useState(false);

  // Volume Analysis States
  const [volumePortfolioData, setVolumePortfolioData] = useState(null);
  const [volumePortfolioLoading, setVolumePortfolioLoading] = useState(false);
  const [volumeChartsByTicker, setVolumeChartsByTicker] = useState({});
  const [volumeChartsLoading, setVolumeChartsLoading] = useState(false);

  // Discounted Value States
  const [discountData, setDiscountData] = useState(null);
  const [discountLoading, setDiscountLoading] = useState(false);

  const fetchStocks = async () => {
    try {
      const res = await api.get("/api/stocks/");
      setStocks(res.data.filter((s) => s.portfolio === Number(id)));
    } catch (error) {
      console.error("Error fetching stocks");
    }
  };

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

  const handleSelectStock = async (stock) => {
    try {
      await api.post("/api/stocks/", {
        ticker: stock.ticker,
        company_name: stock.company_name,
        portfolio: Number(id),
      });
      setSearchQuery("");
      setSearchResults([]);
      setShowDropdown(false);
      fetchStocks();
    } catch (e) {
      console.error("Error adding stock from search");
    }
  };

  const removeStock = async (stockId) => {
    try {
      await api.delete(`/api/stocks/${stockId}/`);
      fetchStocks();
    } catch (e) {
      console.error("Error removing stock");
    }
  };

  const loadPEAnalysis = async () => {
    setPeLoading(true);
    try {
      const res = await api.get(
        `/api/analysis/pe-ratio/?portfolio_id=${id}`
      );
      setPeData(res.data);
    } catch (error) {
      console.error("Error loading PE analysis");
    }
    setPeLoading(false);
  };

  const loadVolumeAnalysis = async () => {
    setVolumePortfolioLoading(true);
    setVolumeChartsLoading(true);
    try {
      const res = await api.get(
        `/api/analysis/volume-portfolio/?portfolio_id=${id}`
      );
      setVolumePortfolioData(res.data);
    } catch (error) {
      console.error("Error loading volume portfolio analysis");
    }
    setVolumePortfolioLoading(false);

    let stocksToUse = stocks;
    if (!stocksToUse || stocksToUse.length === 0) {
      try {
        const res = await api.get("/api/stocks/");
        stocksToUse = res.data.filter((s) => s.portfolio === Number(id));
        setStocks(stocksToUse);
      } catch (error) {
        console.error("Error fetching stocks for volume charts");
        setVolumeChartsLoading(false);
        return;
      }
    }

    try {
      const next = {};
      const results = await Promise.allSettled(
        stocksToUse.map(async (stock) => {
          const res = await api.get(
            `/api/analysis/volume-chart/?ticker=${stock.ticker}`
          );
          return [stock.ticker, res.data.image_url];
        })
      );

      results.forEach((r) => {
        if (r.status === "fulfilled") {
          const [ticker, imageUrl] = r.value;
          next[ticker] = imageUrl;
        }
      });
      setVolumeChartsByTicker(next);
    } catch (error) {
      console.error("Error loading volume charts");
    }
    setVolumeChartsLoading(false);
  };

  const loadDiscountedValue = async () => {
    setDiscountLoading(true);
    try {
      const res = await api.get(
        `/api/analysis/discounted-value/?portfolio_id=${id}`
      );
      setDiscountData(res.data);
    } catch (error) {
      console.error("Error loading discounted value analysis");
    }
    setDiscountLoading(false);
  };

  useEffect(() => {
    fetchStocks();
  }, []);

  return (
    <div className="p-4 sm:p-6">
      <div className="mb-4">
        <Link to="/" className="text-blue-500 hover:text-blue-700 hover:underline flex w-max items-center gap-1 font-medium">
          <span className="text-xl leading-[0] mb-1">&larr;</span> Back to Dashboard
        </Link>
      </div>
      <h2 className="text-xl font-bold mb-4">Portfolio Stocks</h2>

      <div className="flex gap-3 flex-wrap mb-6">
        {/* <button
          onClick={loadVolumeAnalysis}
          className="bg-indigo-600 text-white px-4 py-2 rounded"
        >
          Volume
        </button> */}

        <button
          onClick={() => {
            loadDiscountedValue();
            loadPEAnalysis();
          }}
          className="bg-purple-600 hover:bg-purple-700 transition text-white px-4 py-2 rounded shadow-sm"
        >
          Run PE Analysis
        </button>
        {(peData || discountData) && (
          <button
            onClick={() => {
              setPeData(null);
              setDiscountData(null);
            }}
            className="bg-red-500 hover:bg-red-600 transition text-white px-4 py-2 rounded font-medium shadow-sm"
          >
            Close Analysis
          </button>
        )}
      </div>

      {/* 🔄 Volume Loading */}
      {/* {(volumePortfolioLoading || volumeChartsLoading) && <Spinner />} */}

      {/* 📊 Volume Charts */}
      {/* {volumePortfolioData && (
        <div className="mt-6 bg-white text-gray-900 p-4 shadow rounded">
          <h2 className="text-lg font-bold mb-3">
            Volume Analysis – {volumePortfolioData.portfolio}
          </h2>

          <p className="text-gray-600 text-sm mb-2">
            Portfolio comparison uses average daily volume (3mo).
          </p>

          <img
            src={volumePortfolioData.image_url}
            alt="Volume Portfolio"
            className="w-full rounded"
          />

          {Object.keys(volumeChartsByTicker).length > 0 && (
            <div className="mt-6">
              <h3 className="font-bold mb-3">Per-Stock Volume (6mo)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(volumeChartsByTicker).map(([ticker, url]) => (
                  <div key={ticker} className="bg-gray-50 p-3 rounded border">
                    <div className="font-semibold mb-2">{ticker}</div>
                    <img src={url} alt={`${ticker} volume`} className="w-full rounded" />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )} */}

      {/* 🔄 Loading */}
      {(discountLoading || peLoading) && <Spinner />}

      {/* 📊 Analysis Output */}
      {discountData && (
        <div className="mt-6 bg-white text-gray-900 p-4 shadow rounded">
          <h2 className="text-lg font-bold mb-3">
            Analysis Details – {discountData.portfolio}
          </h2>

          {discountData.rows && discountData.rows.length > 0 && (
            <div className="mt-5 overflow-auto">
              <table className="min-w-full text-sm border">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="text-left p-2 border">Ticker</th>
                    <th className="text-left p-2 border">Price</th>
                    <th className="text-left p-2 border">52W Low</th>
                    <th className="text-left p-2 border">52W High</th>
                    <th className="text-left p-2 border">Position</th>
                  </tr>
                </thead>
                <tbody>
                  {discountData.rows.map((row) => (
                    <tr key={row.ticker}>
                      <td className="p-2 border">{row.ticker}</td>
                      <td className="p-2 border">{row.price}</td>
                      <td className="p-2 border">{row["52w_low"]}</td>
                      <td className="p-2 border">{row["52w_high"]}</td>
                      <td className="p-2 border">{row.position_in_range}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 📊 Charts Grid */}
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Chart 1: 52-Week Low */}
            {discountData.image_url_low && (
              <div className="border p-4 rounded bg-gray-50 flex flex-col h-full">
                <h3 className="text-md font-bold mb-2 text-center">52-Week Low</h3>
                <img
                  src={discountData.image_url_low}
                  alt="52W Low"
                  className="w-full h-auto object-contain rounded my-auto"
                />
              </div>
            )}

            {/* Chart 2: 52-Week High */}
            {discountData.image_url_high && (
              <div className="border p-4 rounded bg-gray-50 flex flex-col h-full">
                <h3 className="text-md font-bold mb-2 text-center">52-Week High</h3>
                <img
                  src={discountData.image_url_high}
                  alt="52W High"
                  className="w-full h-auto object-contain rounded my-auto"
                />
              </div>
            )}

            {/* Chart 3: Discounted Value */}
            {discountData.image_url_discount && (
              <div className="border p-4 rounded bg-gray-50 flex flex-col h-full">
                <h3 className="text-md font-bold mb-2 text-center">Discounted Value (Gap)</h3>
                <img
                  src={discountData.image_url_discount}
                  alt="Discounted Gap"
                  className="w-full h-auto object-contain rounded my-auto"
                />
              </div>
            )}

            {/* Chart 4: PE Ratio Analysis */}
            {peData && peData.image_url && (
              <div className="border p-4 rounded bg-gray-50 flex flex-col h-full">
                <h3 className="text-md font-bold mb-2 text-center">PE Ratio Analysis</h3>
                <img
                  src={peData.image_url}
                  alt="PE Scatter"
                  className="w-full h-auto object-contain rounded my-auto"
                />

                <div className="mt-4 text-xs text-gray-700 bg-white p-2 rounded border">
                  <strong>Legend:</strong><br />
                  🟢 Undervalued (Q1): {peData.undervalued_line} <br />
                  🔴 Overvalued (Q3): {peData.overvalued_line} <br />
                  🟠 Median PE: {peData.median_pe}
                </div>
              </div>
            )}

          </div>
        </div>
      )}

      {/* ➕ Add Stock Form */}
      <div className="mb-6 mt-8 relative w-full max-w-md">
        <h3 className="font-bold mb-2 text-gray-800">Add Stock to Portfolio</h3>
        <input
          type="text"
          placeholder="Search by company name or ticker..."
          className="border p-2 w-full rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setShowDropdown(true);
          }}
          onFocus={() => {
            if (searchResults.length > 0) setShowDropdown(true);
          }}
        />
        {isSearching && <div className="absolute right-3 top-10 text-gray-400 text-sm">Searching...</div>}

        {showDropdown && searchResults.length > 0 && (
          <ul className="absolute z-10 w-full bg-white text-gray-900 border border-gray-200 rounded-b shadow-lg mt-1 max-h-60 overflow-y-auto">
            {searchResults.map((result, idx) => (
              <li
                key={idx}
                className="px-4 py-2 hover:bg-gray-100 cursor-pointer flex justify-between items-center border-b last:border-b-0"
                onClick={() => handleSelectStock(result)}
              >
                <span className="font-medium text-gray-800">{result.company_name}</span>
                <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded">{result.ticker}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* 📈 Individual Stock Price Charts */}
      {stocks.map((stock) => (
        <StockCard key={stock.id} stock={stock} setLoading={setLoading} onRemove={() => removeStock(stock.id)} />
      ))}

      {loading && <Spinner />}
    </div>
  );
};

const StockCard = ({ stock, setLoading, onRemove }) => {
  const [image, setImage] = useState(null);

  const loadChart = async () => {
    setLoading(true);
    try {
      const res = await api.get(
        `/api/analysis/price-chart/?ticker=${stock.ticker}`
      );
      setImage(res.data.image_url);
    } catch (error) {
      console.error("Error loading price chart");
    }
    setLoading(false);
  };

  return (
    <div className="bg-white text-gray-900 p-4 shadow rounded mb-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:justify-between sm:items-start">
        <h3 className="font-bold text-lg break-words">{stock.company_name} <span className="text-gray-500 text-sm ml-2 font-normal">({stock.ticker})</span></h3>
        <button onClick={onRemove} className="text-red-500 hover:text-red-700 transition" title="Remove Stock">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        <button
          onClick={loadChart}
          className="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600 transition shadow-sm"
        >
          Load Chart
        </button>
        {image && (
          <button
            onClick={() => setImage(null)}
            className="bg-gray-500 text-white px-3 py-1 rounded text-sm hover:bg-gray-600 transition shadow-sm"
          >
            Close Chart
          </button>
        )}
      </div>
      {image && <img src={image} alt="chart" className="mt-4 rounded w-full max-w-3xl border shadow-sm" />}
    </div>
  );
};

export default PortfolioDetail;
