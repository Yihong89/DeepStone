import type { CardMeta, GameCard } from "../api/types";

interface CardViewProps {
  card?: CardMeta;
  gameCard?: GameCard;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  selected?: boolean;
}

export default function CardView({ card, gameCard, size = "sm", onClick, selected }: CardViewProps) {
  const h = size === "lg" ? 300 : size === "md" ? 210 : 150;
  const w = Math.round(h * 0.714);
  const name = gameCard?.name ?? card?.name ?? "";
  const cost = gameCard?.cost ?? card?.cost ?? null;
  const type = card?.type ?? (gameCard ? "MINION" : "");
  const attack = gameCard?.atk;
  const health = gameCard && gameCard.max_health != null
    ? gameCard.max_health - (gameCard.damage ?? 0)
    : null;
  const taunt = gameCard?.taunt;
  const canAttack = gameCard?.can_attack;
  const isMinion = gameCard ? attack != null || health != null : type === "MINION";
  const isSpell = gameCard ? !isMinion : type === "SPELL";

  const frame = selected
    ? "border-amber-400 ring-2 ring-amber-400"
    : canAttack
      ? "border-amber-500"
      : taunt
        ? "border-purple-500"
        : "border-slate-600";

  const Tag = onClick ? "button" : "div";
  return (
    <div className="flex flex-col items-center" style={{ width: w }}>
      <Tag
        type={onClick ? "button" : undefined}
        className={`relative overflow-hidden rounded-lg border-2 bg-gradient-to-b from-slate-700 to-slate-900 ${frame} ${onClick ? "cursor-pointer" : ""}`}
        style={{ width: w, height: h }}
        onClick={onClick}
      >
        <div className="absolute inset-0 flex items-center justify-center text-6xl text-slate-600">
          {isSpell ? "✨" : isMinion ? "🛡" : "🎖"}
        </div>
        {cost != null && (
          <span className="absolute left-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-amber-500 text-sm font-bold text-slate-900">
            {cost}
          </span>
        )}
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
        <span className="absolute bottom-1 left-7 right-7 truncate text-center text-xs font-semibold text-slate-100">
          {name}
        </span>
      </Tag>
      {!gameCard && card && card.attack != null && (
        <div className="mt-1 flex w-full justify-between text-xs text-slate-400">
          <span>{card.attack}/{card.health}</span>
          <span>{card.rarity}</span>
        </div>
      )}
    </div>
  );
}
