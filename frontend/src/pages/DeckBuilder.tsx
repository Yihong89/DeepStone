import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import type { CardMeta, Deck } from "../api/types";

const CLASSES = [
  "MAGE", "WARRIOR", "SHAMAN", "ROGUE", "PALADIN", "HUNTER",
  "DRUID", "WARLOCK", "PRIEST", "DEMONHUNTER",
];

export default function DeckBuilder() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [heroClass, setHeroClass] = useState("MAGE");
  const [cards, setCards] = useState<string[]>([]);
  const [pool, setPool] = useState<CardMeta[]>([]);
  const [q, setQ] = useState("");
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    apiFetch<CardMeta[]>(`/cards`).then((all) => setPool(all));
    if (!isNew && id) {
      apiFetch<Deck>(`/decks/${id}`).then((d) => {
        setName(d.name);
        setHeroClass(d.hero_class);
        setCards(d.card_ids);
      });
    }
  }, [id, isNew]);

  const poolById = useMemo(() => Object.fromEntries(pool.map((c) => [c.id, c])), [pool]);
  const classCards = useMemo(
    () => pool.filter((c) => c.cardClass === heroClass || c.cardClass === "NEUTRAL"),
    [pool, heroClass]
  );
  const filtered = useMemo(
    () => classCards.filter((c) => c.name.toLowerCase().includes(q.toLowerCase())),
    [classCards, q]
  );

  function add(cardId: string) {
    const card = poolById[cardId];
    const maxCopies = card.rarity === "LEGENDARY" ? 1 : 2;
    const copies = cards.filter((c) => c === cardId).length;
    if (cards.length >= 30 || copies >= maxCopies) return;
    setCards([...cards, cardId]);
  }
  function removeAt(i: number) {
    setCards(cards.filter((_, idx) => idx !== i));
  }
  function validate(): string[] {
    const errs: string[] = [];
    if (cards.length !== 30) errs.push(`Deck has ${cards.length}/30 cards`);
    const counts: Record<string, number> = {};
    for (const cid of cards) counts[cid] = (counts[cid] ?? 0) + 1;
    for (const [cid, n] of Object.entries(counts)) {
      const card = poolById[cid];
      const max = card?.rarity === "LEGENDARY" ? 1 : 2;
      if (n > max) errs.push(`Too many copies of ${card?.name ?? cid}`);
    }
    return errs;
  }
  async function save() {
    const errs = validate();
    setErrors(errs);
    if (errs.length) return;
    const body = { name, hero_class: heroClass, card_ids: cards };
    if (isNew) await apiFetch<Deck>("/decks", { method: "POST", body: JSON.stringify(body) });
    else await apiFetch<Deck>(`/decks/${id}`, { method: "PUT", body: JSON.stringify(body) });
    navigate("/decks");
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="space-y-4">
        <input
          className="w-full rounded border border-slate-600 bg-slate-800 p-2"
          placeholder="Deck name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select
          className="w-full rounded border border-slate-600 bg-slate-800 p-2"
          value={heroClass}
          onChange={(e) => { setHeroClass(e.target.value); setCards([]); }}
        >
          {CLASSES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <input
          className="w-full rounded border border-slate-600 bg-slate-800 p-2"
          placeholder="Search cards…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="grid max-h-96 grid-cols-3 gap-2 overflow-y-auto">
          {filtered.map((c) => (
            <button
              key={c.id}
              onClick={() => add(c.id)}
              disabled={cards.length >= 30}
              className="rounded border border-slate-700 bg-slate-800 p-2 text-left text-sm hover:border-amber-500 disabled:opacity-40"
            >
              <div className="font-semibold">{c.name}</div>
              <div className="text-slate-400">
                {c.cost} mana · {c.attack ?? "–"}/{c.health ?? "–"}
              </div>
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-3">
        <h3 className="font-bold">Your deck ({cards.length}/30)</h3>
        <div className="max-h-96 space-y-1 overflow-y-auto">
          {cards.map((cid, i) => (
            <div key={i} className="flex items-center justify-between rounded border border-slate-700 bg-slate-800 p-2">
              <span>{poolById[cid]?.name ?? cid}</span>
              <button className="text-red-400" onClick={() => removeAt(i)}>×</button>
            </div>
          ))}
        </div>
        {errors.length > 0 && (
          <ul className="text-sm text-red-400">{errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
        )}
        <button className="w-full rounded bg-amber-500 p-2 font-semibold text-slate-900" onClick={save}>
          Save deck
        </button>
      </div>
    </div>
  );
}
