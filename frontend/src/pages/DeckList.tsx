import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../api/client";
import type { Deck } from "../api/types";

export default function DeckList() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch<Deck[]>("/decks").then(setDecks);
  }, []);

  async function remove(id: number) {
    await apiFetch(`/decks/${id}`, { method: "DELETE" });
    setDecks((d) => d.filter((x) => x.id !== id));
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">My Decks</h2>
        <button
          className="rounded bg-amber-500 px-4 py-2 font-semibold text-slate-900"
          onClick={() => navigate("/decks/new")}
        >
          New deck
        </button>
      </div>
      {decks.length === 0 && <p className="text-slate-400">No decks yet.</p>}
      {decks.map((d) => (
        <div key={d.id} className="flex items-center justify-between rounded border border-slate-700 bg-slate-800 p-3">
          <Link to={`/decks/${d.id}`} className="font-semibold">{d.name}</Link>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400">{d.hero_class}</span>
            <span className="text-sm text-slate-400">{d.card_ids.length}/30</span>
            <button className="text-red-400" onClick={() => remove(d.id)}>Delete</button>
          </div>
        </div>
      ))}
    </div>
  );
}
