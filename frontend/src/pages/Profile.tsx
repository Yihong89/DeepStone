import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import { useAuth } from "../store/auth";

interface MatchRow {
  id: number;
  game_id: string;
  hero1: string;
  hero2: string;
  status: string;
  winner_id: number | null;
  started_at: string;
}

export default function Profile() {
  const user = useAuth((s) => s.user);
  const [matches, setMatches] = useState<MatchRow[]>([]);

  useEffect(() => {
    apiFetch<MatchRow[]>("/matches").then(setMatches).catch(() => setMatches([]));
  }, []);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h2 className="text-2xl font-bold">{user?.username}</h2>
      <p className="text-sm text-slate-400">{user?.email} · {user?.role}</p>
      <h3 className="text-lg font-bold">Match history</h3>
      {matches.length === 0 && <p className="text-slate-400">No matches yet.</p>}
      <ul className="space-y-2">
        {matches.map((m) => (
          <li key={m.id} className="flex justify-between rounded border border-slate-700 bg-slate-800 p-2 text-sm">
            <span>{m.hero1} vs {m.hero2}</span>
            <span className="text-slate-400">
              {m.status}
              {m.winner_id != null && user ? (m.winner_id === user.id ? " · W" : " · L") : ""}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
