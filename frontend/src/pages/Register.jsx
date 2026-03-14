import { useState, useContext } from "react";
import { AuthContext } from "../context/AuthContext";
import { useNavigate, Link } from "react-router-dom";

const Register = () => {
  const { register } = useContext(AuthContext);
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });

  const handleSubmit = async (e) => {
    e.preventDefault();
    await register(form);
    navigate("/login");
  };

  return (
    <div className="flex justify-center px-4 py-8 sm:py-16">
      <form onSubmit={handleSubmit} className="bg-white text-gray-900 p-6 shadow rounded w-full max-w-sm">
        <h2 className="text-xl mb-4">Register</h2>
        <input
          type="text"
          placeholder="Username"
          className="w-full border p-2 mb-3"
          onChange={(e) => setForm({ ...form, username: e.target.value })}
        />
        <input
          type="password"
          placeholder="Password"
          className="w-full border p-2 mb-3"
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        <button className="bg-green-500 text-white w-full p-2 rounded">
          Register
        </button>
        <p className="mt-3 text-sm">
          Already have account? <Link to="/login" className="text-blue-500">Login</Link>
        </p>
      </form>
    </div>
  );
};

export default Register;
