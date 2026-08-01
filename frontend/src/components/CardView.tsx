import { useState } from "react";
import type { CardMeta, GameCard } from "../api/types";

interface CardViewProps {
  card?: CardMeta;
  gameCard?: GameCard;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  selected?: boolean;
}

const TYPE_STYLE: Record<string, { frame: string; badge: string; label: string }> = {
  MINION: { frame: "border-slate-500", badge: "bg-slate-600", label: "Minion" },
  SPELL: { frame: "border-blue-500", badge: "bg-blue-600", label: "Spell" },
  WEAPON: { frame: "border-amber-600", badge: "bg-amber-700", label: "Weapon" },
  HERO: { frame: "border-emerald-600", badge: "bg-emerald-700", label: "Hero" },
  HERO_POWER: { frame: "border-purple-500", badge: "bg-purple-600", label: "Hero Power" },
};
const DEFAULT_STYLE = { frame: "border-slate-600", badge: "bg-slate-600", label: "Card" };

export default function CardView({ card, gameCard, size = "sm", onClick, selected }: CardViewProps) {
  const [hover, setHover] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);
  const h = size === "lg" ? 300 : size === "md" ? 210 : 150;
  const w = Math.round(h * 0.714);
  const name = gameCard?.name ?? card?.name ?? "";
  const cost = gameCard?.cost ?? card?.cost ?? null;
  const text = gameCard?.text ?? card?.text ?? "";
  const type = gameCard?.type ?? card?.type ?? "";
  const id = gameCard?.id ?? card?.id;
  const imgUrl = id && !imgFailed ? `/images/cards/${id}.png` : null;
  const attack = gameCard?.atk ?? card?.attack ?? null;
  const health = gameCard
    ? gameCard.max_health != null
      ? gameCard.max_health - (gameCard.damage ?? 0)
      : null
    : (card?.health ?? null);
  const taunt = gameCard?.taunt;
  const canAttack = gameCard?.can_attack;
  const ts = TYPE_STYLE[type] ?? DEFAULT_STYLE;
  const isMinion = type === "MINION" || (!!gameCard && !type && attack != null);

  const frame = selected
    ? "border-amber-400 ring-2 ring-amber-400"
    : canAttack
      ? "border-amber-500"
      : taunt
        ? "border-purple-500"
        : ts.frame;

  const Tag = onClick ? "button" : "div";
  return (
    <div
      className="relative flex flex-col items-center"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{ width: w }}
    >
      <Tag
        type={onClick ? "button" : undefined}
        className={`relative overflow-hidden rounded-lg border-2 bg-gradient-to-b from-slate-700 to-slate-900 ${frame} ${onClick ? "cursor-pointer" : ""}`}
        style={{ width: w, height: h }}
        onClick={onClick}
      >
        <div className="absolute inset-0 flex items-center justify-center text-6xl text-slate-600">
          {type === "SPELL" ? "✨" : isMinion ? "🛡" : type === "WEAPON" ? "⚔" : "🎖"}
        </div>
        {imgUrl && (
          <img
            src={imgUrl}
            alt={name}
            className="absolute inset-0 h-full w-full object-cover"
            onError={() => setImgFailed(true)}
          />
        )}
        {cost != null && (
          <span className="absolute left-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-amber-500 text-sm font-bold text-slate-900">
            {cost}
          </span>
        )}
        <span className={`absolute right-1 top-1 rounded px-1 py-0.5 text-[8px] font-bold uppercase ${ts.badge}`}>
          {ts.label}
        </span>
        {attack != null && (
          <span className="absolute bottom-1 left-1 flex h-6 w-6 items-center justify-center rounded-full bg-orange-600 text-sm font-bold">
            {attack}
          </span>
        )}
        {health != null && (
          <span className="absolute bottom-1 right-1 flex h-6 w-6 items-center justify-center rounded-full bg-red-600 text-sm font-bold">
            {health}
          </span>
        )}
        <span className="absolute bottom-1 left-7 right-7 line-clamp-2 text-center text-[10px] font-semibold leading-tight text-slate-100">
          {name}
        </span>
      </Tag>
      {hover && (name || text || attack != null || health != null) && (
        <div className="pointer-events-none absolute bottom-full left-1/2 z-50 mb-2 w-56 -translate-x-1/2">
          <div className="rounded-lg border-2 border-slate-500 bg-slate-800 p-3 shadow-xl">
            <div className="flex items-start justify-between gap-2">
              <span className="text-sm font-bold leading-tight text-slate-100">{name}</span>
              {cost != null && (
                <span className="shrink-0 rounded-full bg-amber-500 px-2 py-0.5 text-xs font-bold text-slate-900">
                  {cost}
                </span>
              )}
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${ts.badge}`}>{ts.label}</span>
              {(attack != null || health != null) && (
                <span className="text-xs font-semibold text-slate-300">
                  {attack ?? "–"} / {health ?? "–"}
                </span>
              )}
            </div>
            {text && <p className="mt-2 text-xs leading-snug text-slate-300">{text}</p>}
          </div>
        </div>
      )}
      {!gameCard && card && card.attack != null && (
        <div className="mt-1 flex w-full justify-between text-xs text-slate-400">
          <span>{card.attack}/{card.health}</span>
          <span>{card.rarity}</span>
        </div>
      )}
    </div>
  );
}
