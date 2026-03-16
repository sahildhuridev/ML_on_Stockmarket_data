import { useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";

const Navbar = () => {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();

  return (
    <div className="bg-[#131722] border-b border-white/5 text-white px-4 py-3 sticky top-0 z-50">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <Link to="/" className="font-bold text-lg sm:text-xl tracking-tight flex items-center gap-2">
          <span className="text-blue-500">Sahil</span> Analysis
        </Link>
        {user ? (
          <div className="flex flex-wrap gap-3 sm:gap-6 items-center">
            <Link to="/dashboard" className="text-sm font-medium text-gray-300 hover:text-white transition-colors">Dashboard</Link>
            <span className="text-sm text-gray-400 break-all">Hi {user}</span>
            <button
              onClick={() => {
                logout();
                navigate("/login");
              }}
              className="bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-all"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3 sm:gap-4 items-center">
            <Link to="/login" className="text-sm font-medium text-gray-300 hover:text-white transition-colors">Sign In</Link>
            <Link to="/register" className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition-colors">Get Started</Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default Navbar;
