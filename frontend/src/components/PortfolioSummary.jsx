import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { DollarSign, Layers, TrendingUp, TrendingDown, Folder } from 'lucide-react';

const PortfolioSummary = ({ portfolios }) => {
  const [selectedPortfolio, setSelectedPortfolio] = useState('all');
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchSummary = async (portfolioId) => {
    setLoading(true);
    setError(null);
    try {
      const url = portfolioId === 'all' 
        ? '/api/portfolios/summary/' 
        : `/api/portfolios/summary/?portfolio_id=${portfolioId}`;
        
      const res = await api.get(url);
      setSummaryData(res.data);
    } catch (err) {
      console.error("Error fetching portfolio summary:", err);
      setError("Failed to load portfolio summary. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary(selectedPortfolio);
  }, [selectedPortfolio]);

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2
    }).format(value);
  };

  return (
    <div className="flex flex-col h-full bg-[#1e222d] rounded-lg border border-[#2b2b43] overflow-hidden">
      {/* Header and Filter */}
      <div className="p-6 border-b border-[#2b2b43] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Folder className="w-5 h-5 text-indigo-400" />
            Portfolio Summary
          </h2>
          <p className="text-sm text-gray-400 mt-1">Overview of your investments and current valuation.</p>
        </div>
        
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-400 font-medium">View:</label>
          <select 
            value={selectedPortfolio} 
            onChange={(e) => setSelectedPortfolio(e.target.value)}
            className="bg-[#131722] text-white text-sm border border-[#2b2b43] rounded-md px-3 py-2 outline-none focus:border-indigo-500 transition-colors"
          >
            <option value="all">All Portfolios (Combined)</option>
            {portfolios.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Content Area */}
      <div className="p-6 flex-1 bg-[#131722]/50">
        {loading ? (
          <div className="flex items-center justify-center h-full min-h-[200px]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full min-h-[200px] text-red-400 bg-red-400/10 rounded-lg border border-red-500/20 p-4 text-center">
            {error}
          </div>
        ) : summaryData ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            
            {/* Number of Stocks Card */}
            <div className="bg-[#1e222d] p-5 rounded-xl border border-[#2b2b43] shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-blue-500/5 rounded-full -mr-10 -mt-10 group-hover:bg-blue-500/10 transition-colors"></div>
              <div className="flex items-center justify-between mb-4 relative z-10">
                <h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider">Number of Stocks</h3>
                <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
                  <Layers className="w-5 h-5" />
                </div>
              </div>
              <p className="text-3xl font-bold text-white relative z-10">
                {summaryData.number_of_stocks}
              </p>
            </div>

            {/* Total Invested Card */}
            <div className="bg-[#1e222d] p-5 rounded-xl border border-[#2b2b43] shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full -mr-10 -mt-10 group-hover:bg-purple-500/10 transition-colors"></div>
              <div className="flex items-center justify-between mb-4 relative z-10">
                <h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider">Total Invested</h3>
                <div className="p-2 bg-purple-500/10 rounded-lg text-purple-400">
                  <DollarSign className="w-5 h-5" />
                </div>
              </div>
              <p className="text-2xl font-bold text-white relative z-10">
                {formatCurrency(summaryData.total_invested)}
              </p>
            </div>

            {/* Current Value Card */}
            <div className="bg-[#1e222d] p-5 rounded-xl border border-[#2b2b43] shadow-lg relative overflow-hidden group">
              <div className="absolute top-0 right-0 w-24 h-24 bg-indigo-500/5 rounded-full -mr-10 -mt-10 group-hover:bg-indigo-500/10 transition-colors"></div>
              <div className="flex items-center justify-between mb-4 relative z-10">
                <h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider">Current Value</h3>
                <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
                  <DollarSign className="w-5 h-5" />
                </div>
              </div>
              <p className="text-2xl font-bold text-white relative z-10">
                {formatCurrency(summaryData.total_current_value)}
              </p>
            </div>

            {/* Total Profit/Loss Card */}
            <div className="bg-[#1e222d] p-5 rounded-xl border border-[#2b2b43] shadow-lg relative overflow-hidden group">
              {summaryData.total_profit_loss >= 0 ? (
                <>
                  <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-500/5 rounded-full -mr-10 -mt-10 group-hover:bg-emerald-500/10 transition-colors"></div>
                  <div className="flex items-center justify-between mb-4 relative z-10">
                    <h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider">Total Profit</h3>
                    <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
                      <TrendingUp className="w-5 h-5" />
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-emerald-400 relative z-10">
                    +{formatCurrency(summaryData.total_profit_loss)}
                  </p>
                  <p className="text-xs text-emerald-500/70 mt-2 font-medium">
                    {summaryData.total_invested > 0 
                      ? `+${((summaryData.total_profit_loss / summaryData.total_invested) * 100).toFixed(2)}%`
                      : '0.00%'}
                  </p>
                </>
              ) : (
                <>
                  <div className="absolute top-0 right-0 w-24 h-24 bg-red-500/5 rounded-full -mr-10 -mt-10 group-hover:bg-red-500/10 transition-colors"></div>
                  <div className="flex items-center justify-between mb-4 relative z-10">
                    <h3 className="text-gray-400 text-sm font-medium uppercase tracking-wider">Total Loss</h3>
                    <div className="p-2 bg-red-500/10 rounded-lg text-red-500">
                      <TrendingDown className="w-5 h-5" />
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-red-500 relative z-10">
                    {formatCurrency(summaryData.total_profit_loss)}
                  </p>
                  <p className="text-xs text-red-500/70 mt-2 font-medium">
                    {summaryData.total_invested > 0 
                      ? `${((summaryData.total_profit_loss / summaryData.total_invested) * 100).toFixed(2)}%`
                      : '0.00%'}
                  </p>
                </>
              )}
            </div>
            
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default PortfolioSummary;
