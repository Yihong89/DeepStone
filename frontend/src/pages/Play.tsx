import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import type { Deck } from "../api/types";

export default function Play() {
  const [decks, setDecks] = useState<Deck[]>([]);
  const [deckId, setDeckId] = useState<number | "">("");
  const [code, setCode] = useState("");
  const [createdCode, setCreatedCode] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [params] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch<Deck[]>("/decks").then(setDecks);
    const join = params.get("join");
    if (join) setCode(join);
  }, [params]);

  async function vsAI() {
    if (!deckId) return setMsg("Pick a deck first");
    const { game_id } = await apiFetch<{ game_id: string }>("/games/ai", {
      method: "POST", body: JSON.stringify({ deck_id: deckId }),
    });
    navigate(`/game/${game_id}`);
  }
  async function createChallenge() {
    if (!deckId) return setMsg("Pick a deck first");
    const { code: c } = await apiFetch<{ code: string }>("/games/challenges", {
      method: "POST", body: JSON.stringify({ deck_id: deckId }),
    });
    setCreatedCode(c);
    setMsg(`Share code ${c} — or link: ${location.origin}/play?join=${c}`);
  }
  async function join() {
    if (!code || !deckId) return setMsg("Enter a code and pick a deck");
    const { game_id } = await apiFetch<{ game_id: string }>(`/games/challenges/${code}/join`, {
      method: "POST", body: JSON.stringify({ deck_id: deckId }),
    });
    navigate(`/game/${game_id}`);
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h2 className="text-2xl font-bold">Play</h2>
      <select
        className="w-full rounded border border-slate-600 bg-slate-800 p-2"
        value={deckId}
        onChange={(e) => setDeckId(e.target.value ? Number(e.target.value) : "")}
      >
        <option value="">Choose a deck…</option>
        {decks.map((d) => <option key={d.id} value={d.id}>{d.name} ({d.hero_class})</option>)}
      </select>
      {msg && <p className="text-amber-400">{msg}</p>}
      <button className="w-full rounded bg-amber-500 p-2 font-semibold text-slate-900" onClick={vsAI}>
        Play vs AI
      </button>
      <button
        className="w-full rounded border border-amber-500 p-2 font-semibold text-amber-400"
        onClick={createChallenge}
      >
        Create challenge
      </button>
      {createdCode && (
        <div className="rounded border border-emerald-500 p-3 text-center">
          <div className="text-3xl font-black tracking-widest text-emerald-400">{createdCode}</div>
          <p className="text-sm text-slate-400">Send this code or link to a friend.</p>
        </div>
      )}
      <div className="flex gap-2">
        <input
          className="flex-1 rounded border border-slate-600 bg-slate-800 p-2 uppercase"
          placeholder="JOIN CODE"
          value={code}
          onChange={(e) => setCode(e.target.value.toUpperCase())}
        />
        <button className="rounded bg-slate-700 p-2 font-semibold" onClick={join}>Join</button>
      </div>
    </div>
  );
}
