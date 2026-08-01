import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../api/client";
import type { CardMeta, Deck } from "../api/types";
import CardView from "../components/CardView";

function ManaCurve({ counts, poolById }: { counts: Record<string, number>; poolById: Record<string, CardMeta> }) {
  const buckets = useMemo(() => {
    const arr = new Array(8).fill(0); // 0..6, 7+
    for (const cid of Object.keys(counts)) {
      const cost = poolById[cid]?.cost ?? 0;
      arr[cost >= 7 ? 7 : cost] += counts[cid];
    }
    return arr as number[];
  }, [counts, poolById]);
  const max = Math.max(...buckets, 1);
  return (
    <div>
      <h3 className="font-bold">Mana curve</h3>
      <div className="space-y-1">
        {buckets.map((n, i) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            <span className="w-6 text-right text-slate-400">{i === 7 ? "7+" : i}</span>
            <div className="h-3.5 flex-1 overflow-hidden rounded bg-slate-700">
              <div className="h-full bg-amber-500" style={{ width: `${(n / max) * 100}%` }} />
            </div>
            <span className="w-4 text-slate-300">{n}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const CLASSES = [
  "MAGE", "WARRIOR", "SHAMAN", "ROGUE", "PALADIN", "HUNTER",
  "DRUID", "WARLOCK", "PRIEST", "DEMONHUNTER",
];
const RARITIES = ["FREE", "COMMON", "RARE", "EPIC", "LEGENDARY"];
const TYPES = ["MINION", "SPELL", "WEAPON"];

export default function DeckBuilder() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [heroClass, setHeroClass] = useState("MAGE");
  const [cards, setCards] = useState<string[]>([]);
  const [pool, setPool] = useState<CardMeta[]>([]);
  const [q, setQ] = useState("");
  const [cost, setCost] = useState("");
  const [type, setType] = useState("");
  const [rarity, setRarity] = useState("");
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
  const counts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const cid of cards) m[cid] = (m[cid] ?? 0) + 1;
    return m;
  }, [cards]);

  const typeSummary = useMemo(() => {
    const s: Record<string, number> = {};
    for (const cid of Object.keys(counts)) {
      const type = poolById[cid]?.type ?? "OTHER";
      s[type] = (s[type] ?? 0) + counts[cid];
    }
    return s;
  }, [counts, poolById]);

  const sortedUnique = useMemo(() => {
    return Object.keys(counts).sort((a, b) => {
      const ca = poolById[a]?.cost ?? 0;
      const cb = poolById[b]?.cost ?? 0;
      if (ca !== cb) return ca - cb;
      return (poolById[a]?.name ?? a).localeCompare(poolById[b]?.name ?? b);
    });
  }, [counts, poolById]);
  const classCards = useMemo(
    () => pool.filter((c) => c.cardClass === heroClass || c.cardClass === "NEUTRAL"),
    [pool, heroClass]
  );
  const filtered = useMemo(() => {
    const ql = q.toLowerCase().trim();
    return classCards.filter((c) => {
      if (ql) {
        const hay = `${c.name} ${c.text ?? ""}`.toLowerCase();
        if (!hay.includes(ql)) return false;
      }
      if (cost !== "" && c.cost !== Number(cost)) return false;
      if (type && c.type !== type) return false;
      if (rarity && c.rarity !== rarity) return false;
      return true;
    });
  }, [classCards, q, cost, type, rarity]);

  function add(cardId: string) {
    const card = poolById[cardId];
    const maxCopies = card.rarity === "LEGENDARY" ? 1 : 2;
    const copies = cards.filter((c) => c === cardId).length;
    if (cards.length >= 30 || copies >= maxCopies) return;
    setCards([...cards, cardId]);
  }
  function removeOne(cid: string) {
    const i = cards.indexOf(cid);
    if (i >= 0) setCards(cards.filter((_, idx) => idx !== i));
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
          placeholder="Search name or card text… (e.g. 'draw a card')"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="flex flex-wrap gap-2 text-sm">
          <select
            className="rounded border border-slate-600 bg-slate-800 p-1.5"
            value={type}
            onChange={(e) => setType(e.target.value)}
          >
            <option value="">All types</option>
            {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select
            className="rounded border border-slate-600 bg-slate-800 p-1.5"
            value={cost}
            onChange={(e) => setCost(e.target.value)}
          >
            <option value="">Any cost</option>
            {Array.from({ length: 11 }, (_, i) => <option key={i} value={i}>{i} mana</option>)}
          </select>
          <select
            className="rounded border border-slate-600 bg-slate-800 p-1.5"
            value={rarity}
            onChange={(e) => setRarity(e.target.value)}
          >
            <option value="">Any rarity</option>
            {RARITIES.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <button
            className="rounded border border-slate-600 bg-slate-800 px-2 py-1 text-slate-400 hover:text-slate-200"
            onClick={() => { setQ(""); setCost(""); setType(""); setRarity(""); }}
          >
            Clear
          </button>
        </div>
        <p className="text-xs text-slate-500">Showing {filtered.length} cards</p>
        <div className="grid max-h-96 grid-cols-3 gap-2 overflow-y-auto">
          {filtered.map((c) => (
            <button
              key={c.id}
              onClick={() => add(c.id)}
              disabled={cards.length >= 30}
              className="disabled:opacity-40"
              title={`${c.name} — ${c.text ?? ""}`}
            >
              <CardView card={c} size="sm" />
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-3">
        <h3 className="font-bold">Your deck ({cards.length}/30)</h3>
        <p className="text-xs text-slate-400">
          {(["MINION", "SPELL", "WEAPON"] as const)
            .filter((t) => (typeSummary[t] ?? 0) > 0)
            .map((t) => `${t.toLowerCase()}s: ${typeSummary[t] ?? 0}`)
            .join(" · ")}
        </p>
        <div className="max-h-96 space-y-1 overflow-y-auto">
          {sortedUnique.map((cid) => {
            const c = poolById[cid];
            const count = counts[cid];
            return (
              <div key={cid} className="flex items-center gap-2 rounded border border-slate-700 bg-slate-800 p-1.5">
                <div className="relative shrink-0">
                  <CardView card={c} size="xs" />
                  {count > 1 && (
                    <span className="absolute -right-1.5 -top-1.5 rounded-full bg-amber-500 px-1.5 py-0.5 text-[11px] font-bold text-slate-900">
                      ×{count}
                    </span>
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-semibold">{c?.name ?? cid}</div>
                  <div className="text-xs text-slate-500">{c ? `${c.type} · ${c.cost} mana` : ""}</div>
                </div>
                <button className="text-red-400" onClick={() => removeOne(cid)} title="Remove one copy">−</button>
              </div>
            );
          })}
        </div>
        <ManaCurve counts={counts} poolById={poolById} />
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
