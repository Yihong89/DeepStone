import { useGame } from "../store/game";
import CardView from "./CardView";

export default function ChoiceDialog() {
  const choiceCards = useGame((s) => s.choiceCards);
  const send = useGame((s) => s.send);

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/70">
      <div className="rounded-xl border border-slate-600 bg-slate-800 p-6">
        <h3 className="mb-4 text-center text-xl font-bold text-amber-400">Choose</h3>
        <div className="flex flex-wrap justify-center gap-3">
          {choiceCards.map((c) => (
            <button key={c.entity_id} onClick={() => send({ type: "choice", card: c.entity_id })}>
              <CardView gameCard={c} size="md" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
