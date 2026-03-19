import api from "../api/axios";

export const searchSentimentStocks = async (query) => {
  const { data } = await api.get(`/api/sentiment/search-stocks/?q=${encodeURIComponent(query)}`);
  return data;
};

export const runSentimentAnalysis = async (payload) => {
  const { data } = await api.post("/api/sentiment/run-analysis/", payload);
  return data;
};

export const getSentimentJob = async (jobId) => {
  const { data } = await api.get(`/api/sentiment/jobs/${jobId}/`);
  return data;
};

export const getSentimentResults = async (jobId) => {
  const { data } = await api.get(`/api/sentiment/results/${jobId}/`);
  return data;
};

