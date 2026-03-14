import axios from "axios";

const api = axios.create({
  // we are changing it to /api as we are using https
  //baseURL: "https://ml.sahildhuri.co.in",
  baseURL: "/api",
  //baseURL: "http://4.193.186.30:8001",

});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;