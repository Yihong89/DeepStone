import { useState } from "react";
import type { GameCard } from "../api/types";

interface Props {
  hero: GameCard;
  onClick?: () => void;
  selected?: boolean;
}

export default function HeroView({ hero, onClick, selected }: Props) {
  const [imgFailed, setImgFailed] = useState(false);
  const hp = (hero.max_health ?? 0) - (hero.damage ?? 0);
  const imgUrl = hero.id && !imgFailed ? `/images/cards_board/${hero.id}.png` : null;
  const Tag = onClick ? "button" : "div";
  return (
    <div className="flex flex-col items-center gap-1.5">
      <Tag onClick={onClick} className={`relative block ${onClick ? "cursor-pointer" : ""}`}>
        <div
          className={`h-28 w-28 overflow-hidden rounded-full ring-2 ${
            selected ? "ring-amber-400" : "ring-slate-600"
          } shadow-lg`}
        >
          {imgUrl ? (
            <img
              src={imgUrl}
              alt={hero.name}
              className="h-full w-full object-cover"
              onError={() => setImgFailed(true)}
            />
          ) : (
            <div className="flex h-full w-full items-center justify-center bg-slate-700 text-4xl">🦸</div>
          )}
        </div>
        <span className="absolute -bottom-1 left-1/2 -translate-x-1/2 rounded-full bg-red-600 px-2.5 py-0.5 text-sm font-black text-white shadow">
          {hp}
        </span>
        {hero.armor ? (
          <span className="absolute -right-1 -top-1 rounded-full bg-slate-700 px-1.5 py-0.5 text-xs font-bold text-sky-300 shadow">
            🛡{hero.armor}
          </span>
        ) : null}
      </Tag>
      <span className="text-sm font-semibold text-slate-200">{hero.name}</span>
    </div>
  );
}
