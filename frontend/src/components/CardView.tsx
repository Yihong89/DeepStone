import { useState } from "react";
import type { CardMeta, GameCard } from "../api/types";
import { getKeywords, KEYWORD_DEFS } from "../data/keywords";

interface CardViewProps {
  card?: CardMeta;
  gameCard?: GameCard;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  selected?: boolean;
}

// Real card art is 256x388 (aspect ~0.66); size the frame to match so nothing is cropped.
const ASPECT = 256 / 388;

export default function CardView({ card, gameCard, size = "sm", onClick, selected }: CardViewProps) {
  const [hover, setHover] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);
  const [bigFailed, setBigFailed] = useState(false);
  const h = size === "lg" ? 320 : size === "md" ? 230 : 160;
  const w = Math.round(h * ASPECT);
  const name = gameCard?.name ?? card?.name ?? "";
  const text = gameCard?.text ?? card?.text ?? "";
  const type = gameCard?.type ?? card?.type ?? "";
  const id = gameCard?.id ?? card?.id;
  const imgUrl = id && !imgFailed ? `/images/cards/${id}.png` : null;
  const bigUrl = id && !bigFailed ? `/images/cards_big/${id}.png` : null;
  const canAttack = gameCard?.can_attack;
  const keywords = getKeywords(text);

  // Only a subtle interaction hint — the art itself shows name/cost/stats.
  const ring = selected
    ? "ring-2 ring-amber-400"
    : canAttack
      ? "ring-2 ring-amber-500/80"
      : "";

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
        className={`relative overflow-hidden rounded ${ring} ${onClick ? "cursor-pointer" : ""}`}
        style={{ width: w, height: h }}
        onClick={onClick}
      >
        {imgUrl ? (
          <img src={imgUrl} alt={name} className="h-full w-full object-cover" onError={() => setImgFailed(true)} />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-6xl text-slate-600">
            {type === "SPELL" ? "✨" : type === "WEAPON" ? "⚔" : "🛡"}
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
