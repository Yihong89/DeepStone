import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/client";

export default function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      await register(username, email, password);
      navigate("/login");
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <form onSubmit={onSubmit} className="mx-auto mt-12 max-w-sm space-y-4">
      <h2 className="text-2xl font-bold">Create account</h2>
      <input
        className="w-full rounded border border-slate-600 bg-slate-800 p-2"
        placeholder="Username (min 3 chars)"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        type="email"
        className="w-full rounded border border-slate-600 bg-slate-800 p-2"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        className="w-full rounded border border-slate-600 bg-slate-800 p-2"
        placeholder="Password (min 8 chars)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && <p className="text-red-400">{error}</p>}
      <button className="w-full rounded bg-amber-500 p-2 font-semibold text-slate-900">
        Register
      </button>
      <p className="text-sm text-slate-400">
        Already have an account? <Link to="/login" className="text-amber-400">Sign in</Link>
      </p>
    </form>
  );
}
