import React, { useEffect, useState } from "react";
import api from "../api/axios";
import { Link } from "react-router-dom";
import { LayoutDashboard, TrendingUp, Compass, Plus, Folders, Settings, Target, Cpu } from "lucide-react";

import GoldSilverAnalysis from "../components/GoldSilverAnalysis";
import GoldSilverUnivariateAnalysis from "../components/GoldSilverUnivariateAnalysis";
import CryptocurrencyAnalysis from "../components/CryptocurrencyAnalysis";
import ClusteringAnalysis from "../components/ClusteringAnalysis";
import StockPotentialAnalysis from "../components/StockPotentialAnalysis";
import MovementProbability from "../components/MovementProbability";
import TimeSeriesAnalysis from "../components/TimeSeriesAnalysis";
import ModelAccuracy from "../components/ModelAccuracy";
import MLWorkflow from "../components/MLWorkflow";

const Dashboard = () => {
  const [portfolios, setPortfolios] = useState([]);
  const [name, setName] = useState("");
  const [activeTab, setActiveTab] = useState("overview");

  const fetchPortfolios = async () => {
    const res = await api.get("/api/portfolios/");
    setPortfolios(res.data);
  };

  const createPortfolio = async () => {
    if (!name.trim()) return;
    await api.post("/api/portfolios/", { name });
    setName("");
    fetchPortfolios();
  };

  useEffect(() => {
    fetchPortfolios();
  }, []);

  return (
    <div className="flex h-screen w-full bg-[#131722] text-[#d1d4dc] overflow-hidden font-sans">

      {/* LEFT SIDEBAR (Navigation & Portfolios) */}
      <aside className="w-64 flex-shrink-0 bg-[#1e222d] border-r border-[#2b2b43] flex flex-col z-10">

        {/* Brand Header */}
        <div className="p-5 border-b border-[#2b2b43] flex items-center space-x-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-400 flex items-center justify-center font-bold text-white shadow-lg">
            M
          </div>
          <h1 className="text-xl font-bold tracking-wider text-white">Metrics</h1>
        </div>

        {/* Global Nav */}
        <nav className="p-3 space-y-1">
          <button
            onClick={() => setActiveTab('overview')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md transition-colors ${activeTab === 'overview' ? 'bg-[#2962FF] text-white' : 'text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]'}`}
          >
            <Compass size={18} />
            <span className="font-medium text-sm">Market Overview</span>
          </button>

          <button
            onClick={() => setActiveTab('analysis')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md transition-colors ${activeTab === 'analysis' ? 'bg-[#2962FF] text-white' : 'text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]'}`}
          >
            <TrendingUp size={18} />
            <span className="font-medium text-sm">ML Projections</span>
          </button>

          <button
            onClick={() => setActiveTab('beforeLive')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md transition-colors ${activeTab === 'beforeLive' ? 'bg-[#2962FF] text-white' : 'text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]'}`}
          >
            <Target size={18} />
            <span className="font-medium text-sm">Before Live Market</span>
          </button>

          <button
            onClick={() => setActiveTab('mlflow')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md transition-colors ${activeTab === 'mlflow' ? 'bg-[#2962FF] text-white' : 'text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]'}`}
          >
            <Cpu size={18} />
            <span className="font-medium text-sm">ML Workflow</span>
          </button>

          <button
            onClick={() => setActiveTab('crypto')}
            className={`w-full flex items-center space-x-3 px-3 py-2 rounded-md transition-colors ${activeTab === 'crypto' ? 'bg-[#2962FF] text-white' : 'text-[#787b86] hover:bg-[#2a2e39] hover:text-[#d1d4dc]'}`}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
            <span className="font-medium text-sm flex-1 text-left">Live Market</span>
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          </button>
        </nav>

        {/* Portfolios Section */}
        <div className="flex-1 overflow-y-auto px-3 py-4 mt-2">
          <div className="flex items-center justify-between px-3 mb-2 text-xs font-semibold text-[#5d606b] uppercase tracking-wider">
            <span>Watchlists & Portfolios</span>
            <Folders size={14} />
          </div>

          <div className="space-y-1">
            {portfolios.map((p) => (
              <Link
                key={p.id}
                to={`/portfolio/${p.id}`}
                className="group flex items-center justify-between px-3 py-2 rounded-md hover:bg-[#2a2e39] transition-all"
              >
                <span className="text-sm font-medium text-[#d1d4dc] group-hover:text-white truncate">
                  {p.name}
                </span>
                <div className="w-1.5 h-1.5 rounded-full bg-[#089981] opacity-0 group-hover:opacity-100 transition-opacity"></div>
              </Link>
            ))}
          </div>

          {/* Add Request Row */}
          <div className="mt-4 px-2">
            <div className="bg-[#131722] border border-[#2b2b43] rounded-md flex items-center p-1 focus-within:border-[#2962FF] focus-within:ring-1 focus-within:ring-[#2962FF] transition-all">
              <input
                className="bg-transparent w-full text-sm text-white px-2 py-1 outline-none placeholder-[#5d606b]"
                placeholder="New Portfolio..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && createPortfolio()}
              />
              <button
                onClick={createPortfolio}
                className="p-1 text-[#787b86] hover:text-white hover:bg-[#2a2e39] rounded transition-colors"
                title="Create Portfolio"
              >
                <Plus size={16} />
              </button>
            </div>
          </div>
        </div>

        {/* User / Settings Footer */}
        <div className="p-4 border-t border-[#2b2b43] text-sm text-[#787b86] flex items-center space-x-2 hover:text-[#d1d4dc] cursor-pointer transition-colors">
          <Settings size={16} />
          <span>Settings</span>
        </div>
      </aside>

      {/* MAIN CONTENT STAGE */}
      <main className="flex-1 flex flex-col h-screen overflow-hidden bg-[#131722]">

        {/* Top Action Bar */}
        <header className="h-14 border-b border-[#2b2b43] bg-[#1e222d] flex items-center justify-between px-6 flex-shrink-0 z-20">
          <div className="flex items-center space-x-4 flex-1">
            <h2 className="text-lg font-semibold text-white">
              {activeTab === 'overview' ? 'Global Markets Overview' :
                activeTab === 'analysis' ? 'Machine Learning Projections' :
                  activeTab === 'beforeLive' ? 'Before Live Market — Model Accuracy' :
                    activeTab === 'mlflow' ? 'ML Workflow Pipeline' :
                      'Live Market'}
            </h2>
            <div className="h-4 w-px bg-[#2b2b43] mx-2"></div>
            <div className="hidden md:flex items-center bg-[#131722] border border-[#2b2b43] rounded px-3 py-1.5 w-64 focus-within:border-[#2962FF] transition-colors">
              <svg className="w-4 h-4 text-[#787b86] mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
              <input
                type="text"
                placeholder="Search symbol, analyst..."
                className="bg-transparent text-sm text-[#d1d4dc] outline-none w-full placeholder-[#5d606b]"
              />
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <span className="text-xs text-[#089981] flex items-center bg-[rgba(8,153,129,0.1)] px-3 py-1.5 rounded-full border border-[rgba(8,153,129,0.2)] font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-[#089981] mr-2 animate-pulse"></span>
              Market Open
            </span>
            <div className="h-4 w-px bg-[#2b2b43] mx-1"></div>

            <button className="text-[#787b86] hover:text-white transition-colors p-1.5 rounded hover:bg-[#2a2e39]">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
            </button>
            <button className="text-[#787b86] hover:text-white transition-colors p-1.5 rounded hover:bg-[#2a2e39]">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg>
            </button>

            <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold cursor-pointer hover:ring-2 ring-indigo-400 ring-offset-2 ring-offset-[#1e222d] transition-all ml-2">
              US
            </div>
          </div>
        </header>

        {/* Scrolling Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === 'overview' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <GoldSilverUnivariateAnalysis />
              <GoldSilverAnalysis />
            </div>
          )}

          {activeTab === 'analysis' && (
            <div className="flex flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">

              <TimeSeriesAnalysis />

              {/* Complex modules stacked into grid cards */}
              <div className="w-full">
                <MovementProbability portfolios={portfolios} />
              </div>
              <div className="w-full border border-[#2b2b43] rounded-lg bg-[#1e222d] shadow-xl overflow-hidden">
                <StockPotentialAnalysis portfolios={portfolios} />
              </div>
              <div className="w-full border border-[#2b2b43] rounded-lg bg-[#1e222d] shadow-xl overflow-hidden">
                <ClusteringAnalysis portfolios={portfolios} />
              </div>
            </div>
          )}

          {activeTab === 'beforeLive' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <ModelAccuracy portfolios={portfolios} />
            </div>
          )}

          {activeTab === 'mlflow' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <MLWorkflow portfolios={portfolios} />
            </div>
          )}

          {activeTab === 'crypto' && (
            <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
              <CryptocurrencyAnalysis />
            </div>
          )}
        </div>
      </main>

    </div>
  );
};

export default Dashboard;