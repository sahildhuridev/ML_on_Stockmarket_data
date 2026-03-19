import React, { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  BrainCircuit,
  Download,
  Gauge,
  Loader2,
  Newspaper,
  Radar,
  Search,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import {
  getSentimentJob,
  getSentimentResults,
  runSentimentAnalysis,
  searchSentimentStocks,
} from "../../services/sentimentApi";

const PIE_COLORS = ["#22c55e", "#94a3b8", "#ef4444"];

const MetricCard = ({ icon: Icon, label, value, accent }) => (
  <div className="rounded-2xl border border-[#2b2b43] bg-[linear-gradient(160deg,rgba(30,34,45,0.95),rgba(19,23,34,0.95))] p-4 shadow-[0_20px_45px_rgba(0,0,0,0.18)]">
    <div className="mb-3 flex items-center justify-between">
      <span className="text-[11px] uppercase tracking-[0.25em] text-[#787b86]">{label}</span>
      <div className="rounded-xl border border-white/10 p-2" style={{ color: accent }}>
        <Icon size={16} />
      </div>
    </div>
    <div className="text-2xl font-semibold text-white">{value}</div>
  </div>
);

const WordCloud = ({ words }) => {
  if (!words?.length) {
    return <div className="text-sm text-[#787b86]">No word cloud data available yet.</div>;
  }

  return (
    <div className="flex min-h-[220px] flex-wrap items-center justify-center gap-3 rounded-2xl bg-[radial-gradient(circle_at_top,rgba(41,98,255,0.18),transparent_55%),linear-gradient(180deg,#1e222d,#151925)] p-6">
      {words.slice(0, 24).map((word, index) => (
        <span
          key={`${word.text}-${index}`}
          className="rounded-full border border-white/10 px-3 py-1 font-semibold text-white/90"
          style={{
            fontSize: `${12 + Math.min(word.value, 12) * 2}px`,
            color: index % 3 === 0 ? "#7dd3fc" : index % 3 === 1 ? "#f0abfc" : "#86efac",
            transform: `rotate(${index % 2 === 0 ? -4 : 4}deg)`,
          }}
        >
          {word.text}
        </span>
      ))}
    </div>
  );
};

const SentimentDashboard = () => {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [searching, setSearching] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [job, setJob] = useState(null);
  const [results, setResults] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (!query.trim() || selectedStock?.ticker === query.trim()) {
        setSuggestions([]);
        return;
      }
      setSearching(true);
      try {
        const data = await searchSentimentStocks(query);
        setSuggestions(data || []);
      } catch {
        setSuggestions([]);
      } finally {
        setSearching(false);
      }
    }, 350);

    return () => clearTimeout(timer);
  }, [query, selectedStock]);

  useEffect(() => {
    if (!job?.id || job.status === "completed" || job.status === "failed") return undefined;
    const interval = setInterval(async () => {
      try {
        const nextJob = await getSentimentJob(job.id);
        setJob(nextJob);
        if (nextJob.status === "completed") {
          const resultPayload = await getSentimentResults(nextJob.id);
          setResults(resultPayload);
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [job]);

  const startAnalysis = async () => {
    if (!selectedStock?.ticker) {
      setError("Select a stock first.");
      return;
    }

    setSubmitting(true);
    setError("");
    setResults(null);

    try {
      const response = await runSentimentAnalysis({
        ticker: selectedStock.ticker,
        company_name: selectedStock.company_name,
        window_days: 90,
        force_refresh: false,
      });
      const freshJob = await getSentimentJob(response.job_id);
      setJob(freshJob);
      if (freshJob.status === "completed") {
        const resultPayload = await getSentimentResults(freshJob.id);
        setResults(resultPayload);
      }
    } catch (err) {
      setError(err.response?.data?.error || "Unable to run sentiment analysis.");
    } finally {
      setSubmitting(false);
    }
  };

  const summary = results?.summary_json || {};
  const distribution = results?.distribution_json || [];
  const dailyTrend = results?.daily_trend_json || [];
  const weeklyTrend = results?.weekly_trend_json || [];
  const correlation = results?.correlation_json || {};
  const feed = results?.news_feed_json || [];
  const words = results?.word_cloud_json || [];
  const reportUrl = results?.report?.download_url;

  const correlationTone = useMemo(() => {
    const value = correlation.value || 0;
    if (value > 0.15) return "Positive Link";
    if (value < -0.15) return "Negative Link";
    return "Loose Link";
  }, [correlation]);

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-[#2b2b43] bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.22),transparent_28%),radial-gradient(circle_at_top_right,rgba(34,197,94,0.16),transparent_24%),linear-gradient(180deg,#1e222d,#121621)] p-6 shadow-[0_24px_70px_rgba(0,0,0,0.28)]">
        <div className="grid gap-6 lg:grid-cols-[1.25fr_0.75fr]">
          <div>
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-cyan-400/25 bg-cyan-400/10 px-3 py-1 text-xs uppercase tracking-[0.24em] text-cyan-200">
              <BrainCircuit size={14} />
              Sentimental Analysis
            </div>
            <h2 className="max-w-2xl text-3xl font-semibold tracking-tight text-white">
              Market mood intelligence for a single stock, built from news, earnings, price action, and NLP.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[#9aa0ad]">
              Run a three-month sentiment pass, track momentum and risk, compare narrative shifts with price movement, and export the report.
            </p>

            <div className="relative mt-6">
              <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 backdrop-blur">
                <Search size={18} className="text-[#787b86]" />
                <input
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setSelectedStock(null);
                  }}
                  placeholder="Search ticker or company name"
                  className="w-full bg-transparent text-white outline-none placeholder:text-[#5d606b]"
                />
                {searching && <Loader2 size={16} className="animate-spin text-cyan-300" />}
              </div>

              {!!suggestions.length && !selectedStock && (
                <div className="absolute z-20 mt-2 max-h-72 w-full overflow-y-auto rounded-2xl border border-[#2b2b43] bg-[#161a24] p-2 shadow-2xl">
                  {suggestions.map((stock) => (
                    <button
                      key={stock.ticker}
                      onClick={() => {
                        setSelectedStock(stock);
                        setQuery(`${stock.ticker} - ${stock.company_name}`);
                        setSuggestions([]);
                      }}
                      className="flex w-full items-center justify-between rounded-xl px-3 py-3 text-left transition hover:bg-[#222735]"
                    >
                      <div>
                        <div className="font-semibold text-white">{stock.ticker}</div>
                        <div className="text-sm text-[#8b92a1]">{stock.company_name}</div>
                      </div>
                      <div className="text-xs uppercase tracking-[0.22em] text-[#596071]">{stock.exchange || stock.type || "Equity"}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                onClick={startAnalysis}
                disabled={submitting}
                className="inline-flex items-center gap-2 rounded-2xl bg-[linear-gradient(90deg,#0ea5e9,#2563eb)] px-5 py-3 font-semibold text-white shadow-[0_12px_30px_rgba(14,165,233,0.28)] transition hover:translate-y-[-1px] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                Run Analysis
              </button>
              {selectedStock && (
                <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
                  Tracking <span className="font-semibold">{selectedStock.ticker}</span> over the last 90 days
                </div>
              )}
            </div>

            {error && <div className="mt-4 rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>}
          </div>

          <div className="rounded-[24px] border border-white/10 bg-black/20 p-5 backdrop-blur">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.24em] text-[#787b86]">Pipeline Status</div>
                <div className="mt-2 text-xl font-semibold text-white">{job ? job.status : "Idle"}</div>
              </div>
              <div className="rounded-2xl border border-white/10 p-3 text-cyan-200">
                <Radar size={20} />
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="mb-2 flex items-center justify-between text-xs uppercase tracking-[0.22em] text-[#787b86]">
                  <span>{job?.stage || "waiting"}</span>
                  <span>{job?.progress || 0}%</span>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-[linear-gradient(90deg,#22d3ee,#3b82f6,#22c55e)] transition-all duration-500"
                    style={{ width: `${job?.progress || 0}%` }}
                  />
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <MetricCard icon={Gauge} label="Score" value={results ? `${results.overall_score.toFixed(1)}/10` : "--"} accent="#22d3ee" />
                <MetricCard icon={ShieldAlert} label="Risk" value={results?.risk_indicator || "--"} accent="#f97316" />
              </div>

              {reportUrl && (
                <a
                  href={reportUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  <Download size={16} />
                  Download PDF Report
                </a>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Sparkles} label="Overall Sentiment" value={summary.overall_sentiment || "--"} accent="#22c55e" />
        <MetricCard icon={Gauge} label="Confidence" value={summary.confidence ? `${(summary.confidence * 100).toFixed(0)}%` : "--"} accent="#38bdf8" />
        <MetricCard icon={TrendingUp} label="Momentum" value={summary.momentum || "--"} accent="#a78bfa" />
        <MetricCard icon={ShieldAlert} label="Risk Indicator" value={summary.risk_indicator || "--"} accent="#fb7185" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.05fr_1.2fr]">
        <div className="rounded-[24px] border border-[#2b2b43] bg-[#1a1f2b] p-5">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-[0.24em] text-[#787b86]">Distribution</div>
            <h3 className="mt-2 text-lg font-semibold text-white">Sentiment Mix</h3>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={distribution} dataKey="value" nameKey="label" innerRadius={70} outerRadius={100} paddingAngle={3}>
                  {distribution.map((entry, index) => (
                    <Cell key={entry.label} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-[24px] border border-[#2b2b43] bg-[#1a1f2b] p-5">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-[#787b86]">Trendline</div>
              <h3 className="mt-2 text-lg font-semibold text-white">Daily Sentiment</h3>
            </div>
            <div className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200">{correlationTone}</div>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dailyTrend}>
                <defs>
                  <linearGradient id="sentimentFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#2b2b43" strokeDasharray="4 4" />
                <XAxis dataKey="date" stroke="#787b86" />
                <YAxis stroke="#787b86" />
                <Tooltip />
                <Area type="monotone" dataKey="avg_score" stroke="#22d3ee" fill="url(#sentimentFill)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-[24px] border border-[#2b2b43] bg-[#1a1f2b] p-5">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-[0.24em] text-[#787b86]">Weekly Read</div>
            <h3 className="mt-2 text-lg font-semibold text-white">Weekly Sentiment vs Price Correlation</h3>
          </div>
          <div className="mb-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-[#787b86]">Correlation Value</div>
              <div className="mt-2 text-2xl font-semibold text-white">{typeof correlation.value === "number" ? correlation.value.toFixed(2) : "--"}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.22em] text-[#787b86]">Direction</div>
              <div className="mt-2 text-2xl font-semibold text-white">{correlation.direction || "--"}</div>
            </div>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={weeklyTrend}>
                <CartesianGrid stroke="#2b2b43" strokeDasharray="4 4" />
                <XAxis dataKey="week" stroke="#787b86" />
                <YAxis stroke="#787b86" />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="avg_score" name="Avg Sentiment" stroke="#60a5fa" strokeWidth={2} />
                <Line type="monotone" dataKey="article_count" name="Article Count" stroke="#22c55e" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-[24px] border border-[#2b2b43] bg-[#1a1f2b] p-5">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-[0.24em] text-[#787b86]">Keyword Cloud</div>
            <h3 className="mt-2 text-lg font-semibold text-white">Narrative Density</h3>
          </div>
          <WordCloud words={words} />
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[24px] border border-[#2b2b43] bg-[#1a1f2b] p-5">
          <div className="mb-4 flex items-center gap-3">
            <div className="rounded-2xl border border-white/10 p-3 text-cyan-200">
              <Newspaper size={18} />
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.24em] text-[#787b86]">News Feed</div>
              <h3 className="mt-1 text-lg font-semibold text-white">Latest Articles and Events</h3>
            </div>
          </div>
          <div className="space-y-3">
            {feed.length === 0 && <div className="text-sm text-[#787b86]">Run an analysis to populate the feed.</div>}
            {feed.slice(0, 8).map((item, index) => (
              <a
                key={`${item.title}-${index}`}
                href={item.url || "#"}
                target="_blank"
                rel="noreferrer"
                className="block rounded-2xl border border-white/8 bg-white/[0.03] p-4 transition hover:border-cyan-400/20 hover:bg-white/[0.05]"
              >
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span
                    className={`rounded-full px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] ${
                      item.label === "Positive"
                        ? "bg-emerald-500/15 text-emerald-300"
                        : item.label === "Negative"
                          ? "bg-rose-500/15 text-rose-300"
                          : "bg-slate-500/15 text-slate-300"
                    }`}
                  >
                    {item.label}
                  </span>
                  <span className="text-xs text-[#787b86]">{item.source}</span>
                </div>
                <div className="text-sm font-medium leading-6 text-white">{item.title}</div>
                <div className="mt-2 flex items-center justify-between text-xs text-[#787b86]">
                  <span>{item.published_at ? new Date(item.published_at).toLocaleString() : "Unknown time"}</span>
                  <span>Score {Number(item.score_0_10 || 0).toFixed(1)}</span>
                </div>
              </a>
            ))}
          </div>
        </div>

        <div className="rounded-[24px] border border-[#2b2b43] bg-[#1a1f2b] p-5">
          <div className="mb-4">
            <div className="text-xs uppercase tracking-[0.24em] text-[#787b86]">Job Snapshot</div>
            <h3 className="mt-2 text-lg font-semibold text-white">Execution Detail</h3>
          </div>
          <div className="space-y-3">
            {[
              ["Ticker", selectedStock?.ticker || results?.ticker || "--"],
              ["Company", selectedStock?.company_name || results?.company_name || "--"],
              ["Stage", job?.stage || "--"],
              ["Progress", `${job?.progress || 0}%`],
              ["Articles", summary.article_count || 0],
              ["Embedding Store", results?.embedding_json?.backend || "--"],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/[0.03] px-4 py-3">
                <span className="text-sm text-[#8d95a3]">{label}</span>
                <span className="text-sm font-semibold text-white">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default SentimentDashboard;
