"""Minimal heuristic bot. Returns decision dicts identical to the WS protocol."""


def choose_mulligan(player) -> list[int]:
    """Mulligan cards that cost more than 3 mana."""
    return [c.entity_id for c in player.hand if c.cost > 3]


def _playable(player):
    return [c for c in player.hand if c.is_playable()]


def _valid_target(card):
    if hasattr(card, "targets") and card.targets:
        return card.targets[0].entity_id
    return None


def choose_main_action(player) -> dict:
    # 1) Play the highest-cost playable card (first valid target if needed)
    for card in sorted(_playable(player), key=lambda c: c.cost, reverse=True):
        if card.must_choose_one and card.choose_cards:
            choose = card.choose_cards[0]
        else:
            choose = None
        if hasattr(card, "battlecry_requires_target") and card.battlecry_requires_target() and not card.targets:
            continue
        target = _valid_target(card)
        return {
            "kind": "play_card",
            "card": card.entity_id,
            "target": target,
            "index": 0,
            "choose": choose.entity_id if choose else None,
        }
    # 2) Attack with the highest-attack attacker
    for source in sorted(player.field, key=lambda m: m.atk, reverse=True):
        if source.can_attack():
            targets = source.attack_targets
            if targets:
                return {"kind": "attack", "source": source.entity_id,
                        "target": targets[0].entity_id}
    # 3) Use hero power if usable
    hp = player.hero.power
    if hp is not None and hp.is_playable():
        target = None
        if hasattr(hp, "targets") and hp.targets:
            target = hp.targets[0].entity_id
        return {"kind": "hero_power", "target": target}
    # 4) Otherwise end turn
    return {"kind": "end_turn"}


def choose_choice(player) -> int:
    choice = player.choice
    if choice is None or not choice.cards:
        return 0
    return choice.cards[0].entity_id
