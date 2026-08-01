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
  const imgUrl = hero.id && !imgFailed ? `/images/cards/${hero.id}.png` : null;
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      onClick={onClick}
      className={`relative overflow-hidden rounded ${selected ? "ring-2 ring-amber-400" : ""} ${onClick ? "cursor-pointer" : ""}`}
      style={{ width: 84, height: 127 }}
    >
      {imgUrl ? (
        <img
          src={imgUrl}
          alt={hero.name}
          className="h-full w-full object-cover"
          onError={() => setImgFailed(true)}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-4xl text-slate-500">🦸</div>
      )}
      <div className="absolute inset-0 flex flex-col justify-between p-1">
        <div className="flex justify-center">
          {hero.armor ? (
            <span className="rounded-full bg-slate-700/90 px-1.5 py-0.5 text-[11px] font-bold text-sky-300">
              🛡 {hero.armor}
            </span>
          ) : null}
        </div>
        <div className="flex justify-center">
          <span className="rounded-full bg-red-600 px-2 py-0.5 text-sm font-black text-white shadow">
            {hp}
          </span>
        </div>
      </div>
    </Tag>
  );
}
