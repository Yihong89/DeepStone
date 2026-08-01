import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import type { GameCard } from "../api/types";
import CardView from "../components/CardView";
import ChoiceDialog from "../components/ChoiceDialog";
import HeroView from "../components/HeroView";
import TargetingOverlay from "../components/TargetingOverlay";
import { useAuth } from "../store/auth";
import { useGame } from "../store/game";

interface Selection {
  type: "attack" | "play" | "hero_power";
  source: GameCard;
}

function SecretMarker() {
  return (
    <div className="flex h-20 w-14 items-center justify-center rounded border-2 border-purple-400 bg-gradient-to-b from-purple-800 to-purple-950 text-2xl font-black text-purple-200 shadow">
      ?
    </div>
  );
}

function ManaCrystals({ available, total }: { available: number; total: number }) {
  const crystals = Math.max(total, available);
  return (
    <div className="flex items-center gap-2">
      <div className="flex gap-1">
        {Array.from({ length: crystals }, (_, i) => (
          <span
            key={i}
            className={`h-4 w-4 rounded-full ${i < available ? "bg-amber-400" : "bg-slate-600"}`}
          />
        ))}
      </div>
      <span className="text-xs font-semibold text-slate-300">{available}/{total}</span>
    </div>
  );
}

export default function GameBoard() {
  const { gameId } = useParams();
  const token = useAuth((s) => s.token);
  const state = useGame((s) => s.state);
  const pending = useGame((s) => s.pending);
  const mulliganCards = useGame((s) => s.mulliganCards);
  const connect = useGame((s) => s.connect);
  const send = useGame((s) => s.send);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [targets, setTargets] = useState<number[]>([]);
  const [mulliganToggle, setMulliganToggle] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (gameId && token) connect(gameId, token);
    return () => useGame.getState().reset();
  }, [gameId, token, connect]);

  const me = state?.players[0];
  const opp = state?.players[1];
  const yourTurn = state ? state.current_player === 0 && !state.ended : false;
  const hero = me?.hero;
  const heroPower = me?.hero_power;

  const targetIds = useMemo(() => new Set(targets), [targets]);
  const mulliganHand = useMemo(
    () => (me ? me.hand.filter((c) => mulliganCards.includes(c.entity_id)) : []),
    [me, mulliganCards]
  );
  const log = useGame((s) => s.log);
  const logRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [log]);

  function clearSelection() {
    setSelection(null);
    setTargets([]);
  }

  function onMyMinion(card: GameCard) {
    if (selection) return clearSelection();
    if (yourTurn && card.can_attack) {
      setSelection({ type: "attack", source: card });
      setTargets(card.attack_targets ?? []);
    }
  }

  function onMyHand(card: GameCard) {
    if (selection) return clearSelection();
    if (!yourTurn) return;
    if ((card.cost ?? 0) > (me?.mana ?? 0)) return;
    if (card.requires_target && (card.targets ?? []).length > 0) {
      setSelection({ type: "play", source: card });
      setTargets(card.targets ?? []);
    } else {
      send({
        type: "action",
        action: { kind: "play_card", card: card.entity_id, target: null, index: 0, choose: null },
      });
    }
  }

  function onOppCharacter(card: GameCard) {
    if (!selection) return;
    if (targetIds.has(card.entity_id)) {
      if (selection.type === "attack") {
        send({ type: "action", action: { kind: "attack", source: selection.source.entity_id, target: card.entity_id } });
      } else if (selection.type === "play") {
        send({
          type: "action",
          action: { kind: "play_card", card: selection.source.entity_id, target: card.entity_id, index: 0, choose: null },
        });
      } else {
        send({ type: "action", action: { kind: "hero_power", target: card.entity_id } });
      }
    }
    clearSelection();
  }

  function useHeroPower() {
    if (!yourTurn || !heroPower?.can_play) return;
    if ((heroPower.targets ?? []).length > 0) {
      setSelection({ type: "hero_power", source: heroPower });
      setTargets(heroPower.targets ?? []);
    } else {
      send({ type: "action", action: { kind: "hero_power", target: null } });
    }
  }

  function endTurn() {
    if (yourTurn) send({ type: "action", action: { kind: "end_turn" } });
  }

  function toggleMulligan(eid: number) {
    const next = new Set(mulliganToggle);
    if (next.has(eid)) next.delete(eid);
    else next.add(eid);
    setMulliganToggle(next);
  }

  if (!state) {
    return <p className="p-8 text-center text-slate-400">Connecting to game…</p>;
  }

  const selectionLabel = selection
    ? selection.type === "attack"
      ? "Choose a target to attack"
      : selection.type === "play"
        ? "Choose a target for your card"
        : "Choose a hero power target"
    : null;

  return (
    <div className="relative flex gap-4">
      <div className="flex min-h-[80vh] flex-1 flex-col justify-between gap-3">
      {selectionLabel && <TargetingOverlay label={selectionLabel} onCancel={clearSelection} />}

      {/* Opponent zone */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-sm text-slate-300">
          <span>{opp!.hero.name ?? "Opponent"}</span>
          <span>Deck: {opp!.deck_count} · Hand: {opp!.hand.length}</span>
        </div>
        <div className="flex justify-center">
          <ManaCrystals available={opp!.mana} total={opp!.max_mana} />
        </div>
        <div className="flex gap-2">
          {opp!.field.map((m) => (
            <CardView
              key={m.entity_id}
              gameCard={m}
              onClick={() => onOppCharacter(m)}
              selected={targetIds.has(m.entity_id)}
            />
          ))}
        </div>
        <div className="flex items-center justify-center gap-2">
          <HeroView
            hero={opp!.hero}
            onClick={() => onOppCharacter(opp!.hero)}
            selected={targetIds.has(opp!.hero.entity_id)}
          />
          {opp!.secrets.map((s) => <SecretMarker key={s.entity_id} />)}
        </div>
      </section>

      {/* Status + actions */}
      <section className="flex items-center justify-center gap-4">
        <span className={`rounded px-3 py-1 font-semibold ${yourTurn ? "bg-amber-500 text-slate-900" : "bg-slate-700 text-slate-300"}`}>
          {yourTurn ? "Your turn" : "Opponent's turn"} · Turn {state.turn}
        </span>
        <button onClick={endTurn} disabled={!yourTurn}
          className="rounded bg-slate-700 px-4 py-1 font-semibold disabled:opacity-40">End turn</button>
        <button onClick={useHeroPower} disabled={!yourTurn || !heroPower?.can_play}
          className="rounded bg-slate-700 px-4 py-1 font-semibold disabled:opacity-40">
          Hero power ({heroPower?.cost ?? "–"})
        </button>
      </section>

      {/* Player zone */}
      <section className="space-y-2">
        <div className="flex items-center justify-center gap-2">
          <HeroView hero={hero!} />
          {me!.secrets.map((s) => <CardView key={s.entity_id} gameCard={s} size="xs" />)}
        </div>
        <div className="flex justify-center">
          <ManaCrystals available={me!.mana} total={me!.max_mana} />
        </div>
        <div className="flex gap-2">
          {me!.field.map((m) => (
            <CardView key={m.entity_id} gameCard={m} onClick={() => onMyMinion(m)} />
          ))}
        </div>
        <div className="flex min-h-[110px] items-end justify-center gap-2 rounded border border-slate-700 bg-slate-800/50 p-2">
          {me!.hand.map((c) => (
            <CardView key={c.entity_id} gameCard={c} onClick={() => onMyHand(c)} />
          ))}
        </div>
      </section>
      </div>

      <aside className="w-72 shrink-0">
        <h3 className="mb-2 text-sm font-bold text-slate-300">Battle history</h3>
        <div ref={logRef} className="max-h-[70vh] space-y-1 overflow-y-auto">
          {log.map((m, i) => (
            <div key={i} className="rounded bg-slate-800/60 px-2 py-1 text-xs text-slate-400">{m}</div>
          ))}
          {log.length === 0 && <p className="text-xs text-slate-600">No events yet.</p>}
        </div>
      </aside>

      {pending === "choice" && <ChoiceDialog />}

      {pending === "mulligan" && (
        <div className="fixed inset-0 z-20 bg-black/70 p-8">
          <h3 className="text-center text-xl font-bold text-amber-400">
            Mulligan — click cards to swap, or keep all
          </h3>
          <div className="mt-4 flex flex-wrap justify-center gap-3">
            {mulliganHand.map((c) => (
              <button key={c.entity_id} onClick={() => toggleMulligan(c.entity_id)}>
                <CardView gameCard={c} size="md" selected={mulliganToggle.has(c.entity_id)} />
              </button>
            ))}
          </div>
          <div className="mt-6 flex justify-center gap-4">
            <button
              className="rounded bg-emerald-500 px-6 py-2 font-semibold text-slate-900"
              onClick={() => { send({ type: "mulligan", cards: [] }); setMulliganToggle(new Set()); }}
            >
              Keep all
            </button>
            <button
              className="rounded bg-red-500 px-6 py-2 font-semibold"
              onClick={() => { send({ type: "mulligan", cards: [...mulliganToggle] }); setMulliganToggle(new Set()); }}
            >
              Swap selected
            </button>
          </div>
        </div>
      )}

      {state.ended && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/80">
          <div className="rounded-xl border border-slate-600 bg-slate-800 p-8 text-center">
            <h2 className="text-3xl font-black">
              {state.result?.winner === 0 ? "🏆 You win!" : state.result?.winner === 1 ? "You lose" : "Draw"}
            </h2>
            <p className="mt-2 text-slate-400">
              {state.result?.playstates?.join(" vs ") ?? "Game over"}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
