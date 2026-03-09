import { createContext, useState, useEffect } from "react";
import api from "../api/axios";

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);

  const login = async (data) => {
    const res = await api.post("/api/accounts/login/", data);
    localStorage.setItem("access", res.data.access);
    localStorage.setItem("refresh", res.data.refresh);
    await getUser();
  };

  const register = async (data) => {
    await api.post("/api/accounts/register/", data);
  };

  const logout = () => {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    setUser(null);
  };

  const getUser = async () => {
    try {
      const res = await api.get("/api/accounts/me/");
      setUser(res.data.username);
    } catch {
      logout();
    }
  };

  useEffect(() => {
    if (localStorage.getItem("access")) {
      getUser();
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};