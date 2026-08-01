from collections import Counter

from .carddata import get_card_map


def validate_deck(hero_class: str, card_ids: list[str]) -> list[str]:
    """Return a list of validation error messages; empty list means valid."""
    errors: list[str] = []
    if len(card_ids) != 30:
        errors.append("A deck must contain exactly 30 cards")
        return errors
    card_map = get_card_map()
    counts = Counter(card_ids)
    for cid, count in counts.items():
        card = card_map.get(cid)
        if card is None:
            errors.append(f"Unknown card: {cid}")
            continue
        cc = card["cardClass"]
        if cc not in (hero_class, "NEUTRAL"):
            errors.append(f"{card['name']} cannot be used in a {hero_class} deck")
        if card["rarity"] == "LEGENDARY":
            if count > 1:
                errors.append(f"Only 1 copy of legendary card {card['name']} allowed")
        elif count > 2:
            errors.append(f"Only 2 copies of {card['name']} allowed")
    return errors
