import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";
import type { CardMeta } from "../api/types";
import CardView from "../components/CardView";

const CLASSES = [
  "MAGE", "WARRIOR", "SHAMAN", "ROGUE", "PALADIN", "HUNTER",
  "DRUID", "WARLOCK", "PRIEST", "DEMONHUNTER", "NEUTRAL",
];

export default function Gallery() {
  const [cards, setCards] = useState<CardMeta[]>([]);
  const [q, setQ] = useState("");
  const [cls, setCls] = useState("");
  const [cost, setCost] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (cls) params.set("class", cls);
    if (cost !== "") params.set("cost", cost);
    apiFetch<CardMeta[]>(`/cards?${params.toString()}`).then((c) => {
      setCards(c);
      setLoading(false);
    });
  }, [q, cls, cost]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <input
          className="rounded border border-slate-600 bg-slate-800 p-2"
          placeholder="Search cards…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="rounded border border-slate-600 bg-slate-800 p-2"
          value={cls}
          onChange={(e) => setCls(e.target.value)}
        >
          <option value="">All classes</option>
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select
          className="rounded border border-slate-600 bg-slate-800 p-2"
          value={cost}
          onChange={(e) => setCost(e.target.value)}
        >
          <option value="">Any cost</option>
          {Array.from({ length: 11 }, (_, i) => <option key={i} value={i}>{i}</option>)}
        </select>
      </div>
      {loading ? <p>Loading…</p> : (
        <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
          {cards.map((c) => <CardView key={c.id} card={c} size="sm" />)}
        </div>
      )}
    </div>
  );
}
