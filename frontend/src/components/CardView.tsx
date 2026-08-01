import { useState } from "react";
import type { CardMeta, GameCard } from "../api/types";
import { getKeywords, KEYWORD_DEFS } from "../data/keywords";

interface CardViewProps {
  card?: CardMeta;
  gameCard?: GameCard;
  size?: "xs" | "sm" | "md" | "lg";
  onClick?: () => void;
  selected?: boolean;
  dataEid?: number;
}

// Real card art is 256x388 (aspect ~0.66); size the frame to match so nothing is cropped.
const ASPECT = 256 / 388;

export default function CardView({ card, gameCard, size = "sm", onClick, selected, dataEid }: CardViewProps) {
  const [hover, setHover] = useState(false);
  const [boardFailed, setBoardFailed] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);
  const [bigFailed, setBigFailed] = useState(false);
  // A character in play (board minion) uses the raw square art and a square tile;
  // everything else uses the framed card render (portrait aspect).
  const isBoardChar = gameCard?.max_health != null;
  const baseH = size === "lg" ? 320 : size === "md" ? 230 : size === "xs" ? 104 : 160;
  const h = isBoardChar ? Math.round(baseH * 0.7) : baseH;
  const w = isBoardChar ? h : Math.round(h * ASPECT);
  const name = gameCard?.name ?? card?.name ?? "";
  const text = gameCard?.text ?? card?.text ?? "";
  const type = gameCard?.type ?? card?.type ?? "";
  const id = gameCard?.id ?? card?.id;
  const attack = gameCard?.atk ?? card?.attack ?? null;
  // Board minions prefer the raw square art; fall back to the framed card if it's
  // unavailable so a minion never shows as an empty shield.
  const boardImgUrl = id && isBoardChar && !boardFailed ? `/images/cards_board/${id}.png` : null;
  const framedImgUrl = id && !imgFailed ? `/images/cards/${id}.png` : null;
  const imgUrl = isBoardChar ? (boardImgUrl ?? framedImgUrl) : framedImgUrl;
  const bigUrl = id && !bigFailed ? `/images/cards_big/${id}.png` : null;
  const canAttack = gameCard?.can_attack;
  const keywords = getKeywords(text);

  // Live stats for minions on the board (the art shows base, not current HP).
  const currentHp =
    gameCard && gameCard.max_health != null
      ? Math.max(0, gameCard.max_health - (gameCard.damage ?? 0))
      : null;
  const damaged = currentHp != null && gameCard?.max_health != null && currentHp < gameCard.max_health;

  // Only a subtle interaction hint — the art itself shows name/cost/stats.
  // Taunt minions always carry a purple aura so they stand out on the battlefield.
  const taunt = gameCard?.taunt;
  const tauntAura = taunt ? "shadow-[0_0_14px_rgba(168,85,247,0.6)]" : "";
  const ring = selected
    ? "ring-2 ring-amber-400"
    : canAttack
      ? "ring-2 ring-amber-500/80"
      : "";

  const Tag = onClick ? "button" : "div";
  return (
    <div
      className="relative flex flex-col items-center"
      data-eid={dataEid}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{ width: w }}
    >
      <Tag
        type={onClick ? "button" : undefined}
        className={`relative overflow-hidden rounded ${ring} ${tauntAura} ${onClick ? "cursor-pointer" : ""}`}
        style={{ width: w, height: h }}
        onClick={onClick}
      >
        {imgUrl ? (
          <img
            src={imgUrl}
            alt={name}
            className="h-full w-full object-cover"
            onError={() => (isBoardChar && boardImgUrl ? setBoardFailed(true) : setImgFailed(true))}
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-6xl text-slate-600">
            {type === "SPELL" ? "✨" : type === "WEAPON" ? "⚔" : "🛡"}
          </div>
        )}
        {taunt && (
          <span className="absolute left-1 top-1 rounded bg-purple-600/90 px-1 py-0.5 text-[9px] font-bold uppercase text-white shadow">
            Taunt
          </span>
        )}
        {/* Live attack / HP on board minions */}
        {gameCard && attack != null && currentHp != null && (
          <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between p-1">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-orange-600 text-xs font-black text-white shadow">
              {attack}
            </span>
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-black text-white shadow ${
                damaged ? "bg-red-600" : "bg-slate-600"
              }`}
            >
              {currentHp}
            </span>
          </div>
        )}
      </Tag>

      {/* Big hi-res popup, always centered in the viewport */}
      {hover && bigUrl && (
        <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center">
          <div className="flex items-center gap-6">
            <img
              src={bigUrl}
              alt={name}
              className="h-[420px] rounded-lg shadow-2xl"
              onError={() => setBigFailed(true)}
            />
            {keywords.length > 0 && (
              <div className="max-w-xs space-y-2">
                {keywords.map((k) => (
                  <div key={k} className="rounded-lg border border-slate-600 bg-slate-800/95 p-3 shadow-xl">
                    <div className="text-sm font-bold text-amber-300">{k}</div>
                    <div className="mt-0.5 text-xs leading-snug text-slate-300">{KEYWORD_DEFS[k]}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
