import axios from "axios";

const api = axios.create({
  baseURL: "http://4.193.186.30:8001/",
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;