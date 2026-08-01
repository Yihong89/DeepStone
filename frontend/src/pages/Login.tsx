import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, me } from "../api/client";
import { useAuth } from "../store/auth";

export default function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const { setToken, setUser } = useAuth();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const res = await login(username, password);
      setToken(res.access_token);
      const user = await me();
      setUser(user);
      navigate("/");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto mt-12 max-w-sm space-y-4">
      <h2 className="text-2xl font-bold">Sign in</h2>
      <input
        className="w-full rounded border border-slate-600 bg-slate-800 p-2"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        type="password"
        className="w-full rounded border border-slate-600 bg-slate-800 p-2"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && <p className="text-red-400">{error}</p>}
      <button className="w-full rounded bg-amber-500 p-2 font-semibold text-slate-900">
        Sign in
      </button>
      <p className="text-sm text-slate-400">
        New here? <Link to="/register" className="text-amber-400">Create an account</Link>
      </p>
    </form>
  );
}
