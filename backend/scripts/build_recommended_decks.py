"""Build recommended_decks.json from curated strong deck lists.

Deck card names are resolved against the local cards.json (the engine's own card
universe, through Scholomance Academy). Cards not found are reported so the list
can be adjusted. Each deck is filled to exactly 30 cards with legal copies.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CARDS = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cards.json")))
BY_NAME = {}
for c in CARDS:
    BY_NAME.setdefault(c["name"].lower(), []).append(c)
BY_ID = {c["id"]: c for c in CARDS}

# name -> (copies). Names that don't resolve are reported.
DECKS = [
    {
        "name": "Aggro Demon Hunter",
        "hero_class": "DEMONHUNTER",
        "cards": {
            "Twin Slice": 2, "Battlefiend": 2, "Chaos Strike": 2, "Umberwing": 2,
            "Satyr Overseer": 2, "Illidari Felblade": 1, "Altruis the Outcast": 1,
            "Glaivebound Adept": 2, "Skull of Gul'dan": 2, "Guardian Augmerchant": 2,
            "Blazing Battlemage": 2, "Beaming Sidekick": 2, "Bonechewer Brawler": 2,
            "Amani Berserker": 2, "Frozen Shadoweaver": 2, "Cobalt Spellkin": 2,
        },
        "tips": "Aggressive tempo: flood the board early and go face. Mulligan for Battlefiend and 1-drops; play Skull of Gul'dan on 5 to refuel.",
    },
    {
        "name": "Tempo Mage",
        "hero_class": "MAGE",
        "cards": {
            "Arcane Breath": 1, "Ray of Frost": 1, "Firebrand": 1, "Combustion": 1,
            "Frost Nova": 1, "Arcane Intellect": 1, "Conjurer's Calling": 1,
            "Rolling Fireball": 1, "Malygos, Aspect of Magic": 1, "Reno the Relicologist": 1,
            "Dragoncaster": 1, "Power of Creation": 1, "Deep Freeze": 1,
            "Puzzle Box of Yogg-Saron": 1, "Kalecgos": 1, "The Amazing Reno": 1,
            "Primordial Studies": 1, "Brain Freeze": 1, "Devolving Missiles": 1,
            "Doomsayer": 1, "Zephrys the Great": 1, "Twilight Drake": 1,
            "Escaped Manasaber": 1, "Jandice Barov": 1, "Khartut Defender": 1,
            "Siamat": 1, "Alexstrasza": 1, "Dragonqueen Alexstrasza": 1,
        },
        "tips": "Highlander value control. Keep no duplicates to enable Reno and Zephrys; clear boards then out-value the opponent.",
    },
    {
        "name": "Zoo Warlock",
        "hero_class": "WARLOCK",
        "cards": {
            "Flame Imp": 2, "Voidwalker": 2, "Mortal Coil": 2, "Soulfire": 2,
            "Knife Juggler": 2, "Dire Wolf Alpha": 2, "Harvest Golem": 2,
            "Defender of Argus": 2, "Doomguard": 2, "Imp Gang Boss": 2,
            "Void Terror": 1, "Power Overwhelming": 2, "Abusive Sergeant": 2,
            "Dark Iron Dwarf": 2, "Voidcaller": 1, "Sylvanas Windrunner": 1,
            "Dr. Boom": 1,
        },
        "tips": "Classic aggro: flood the board, buff with Dire Wolf Alpha, burst with Power Overwhelming + Doomguard. Trade only to protect your board.",
    },
    {
        "name": "Control Warrior",
        "hero_class": "WARRIOR",
        "cards": {
            "Shield Slam": 2, "Shield Block": 2, "Execute": 2, "Fiery War Axe": 2,
            "Slam": 2, "Brawl": 2, "Armorsmith": 2, "Acolyte of Pain": 2,
            "Grommash Hellscream": 1, "Gorehowl": 1, "Sylvanas Windrunner": 1,
            "Dr. Boom": 1, "Harrison Jones": 1, "Shieldmaiden": 2, "Baron Geddon": 1,
            "Ragnaros the Firelord": 1, "Ironbeak Owl": 1, "Loot Hoarder": 2,
        },
        "tips": "Control: gain armor and answer everything with Shield Slam/Execute/Brawl. Win with big legendaries or Grommash + a way to enrage him.",
    },
    {
        "name": "Freeze Mage",
        "hero_class": "MAGE",
        "cards": {
            "Frostbolt": 2, "Ice Lance": 2, "Fireball": 2, "Frost Nova": 2,
            "Blizzard": 2, "Flamestrike": 2, "Ice Block": 2, "Ice Barrier": 2,
            "Doomsayer": 2, "Archmage Antonidas": 1, "Alexstrasza": 1,
            "Mad Scientist": 2, "Arcane Intellect": 2, "Loot Hoarder": 2,
            "Novice Engineer": 2,
        },
        "tips": "Stall with freezes and secrets, drop Alexstrasza to 15, then burst with Frostbolt + Ice Lance + Fireball. Antonidas + cheap spells wins the long game.",
    },
    {
        "name": "Face Hunter",
        "hero_class": "HUNTER",
        "cards": {
            "Leper Gnome": 2, "Abusive Sergeant": 2, "Wolfrider": 2,
            "Knife Juggler": 2, "Animal Companion": 2, "Kill Command": 2,
            "Arcane Golem": 2, "Eaglehorn Bow": 2, "Quick Shot": 2, "Explosive Trap": 2,
            "Freezing Trap": 2, "Mad Scientist": 2, "Haunted Creeper": 2,
            "Savannah Highmane": 2, "Leeroy Jenkins": 1, "Houndmaster": 1,
        },
        "tips": "Go face always. Use hero power every turn; Kill Command + weapons close out games. Mulligan for low drops.",
    },
    {
        "name": "Midrange Paladin",
        "hero_class": "PALADIN",
        "cards": {
            "Shielded Minibot": 2, "Muster for Battle": 2, "Aldor Peacekeeper": 2,
            "Truesilver Champion": 2, "Consecration": 2, "Piloted Shredder": 2,
            "Loatheb": 1, "Sludge Belcher": 2, "Tirion Fordring": 1,
            "Knife Juggler": 2, "Coghammer": 1, "Blessing of Kings": 2,
            "Argent Protector": 2, "Loot Hoarder": 2, "Acolyte of Pain": 2,
            "Dr. Boom": 1, "Harrison Jones": 1,
        },
        "tips": "Curve out with sticky minions and weapons, buff with Blessing of Kings, finish with Tirion and Dr. Boom. Keep board control with Consecration.",
    },
    {
        "name": "Tempo Rogue",
        "hero_class": "ROGUE",
        "cards": {
            "Backstab": 2, "Deadly Poison": 2, "Eviscerate": 2, "SI:7 Agent": 2,
            "Azure Drake": 2, "Fan of Knives": 1, "Sap": 2, "Perdition's Blade": 1,
            "Leeroy Jenkins": 1, "Edwin VanCleef": 1, "Blade Flurry": 2,
            "Violet Teacher": 2, "Defias Ringleader": 2, "Bloodmage Thalnos": 1,
            "Loot Hoarder": 2, "Gnomish Inventor": 2, "Assassin's Blade": 1,
            "Cold Blood": 2,
        },
        "tips": "Tempo: use cheap spells to fight for board, then burst with Cold Blood/Leeroy. Edwin on a big combo turn wins games.",
    },
    {
        "name": "Totem Shaman",
        "hero_class": "SHAMAN",
        "cards": {
            "Flametongue Totem": 2, "Lightning Bolt": 2, "Rockbiter Weapon": 2,
            "Totemic Might": 2, "Mana Tide Totem": 2, "Vitality Totem": 1,
            "Windspeaker": 1, "Stormforged Axe": 1, "Lava Burst": 2, "Hex": 2,
            "Lightning Storm": 2, "Azure Drake": 2, "Feral Spirit": 2, "Bloodlust": 1,
            "Doomhammer": 1, "Al'Akir the Windlord": 1, "Thrallmar Farseer": 1,
            "Knife Juggler": 1, "Frost Shock": 2,
        },
        "tips": "Spam totems, buff them with Flametongue, finish with Bloodlust or Rockbiter + Al'Akir. Keep the board wide.",
    },
]

MISSING = {}


def resolve(name: str) -> str | None:
    key = name.lower()
    if key in MISSING:
        return None
    if key in BY_NAME:
        # prefer class-relevant card
        return BY_NAME[key][0]["id"]
    MISSING[key] = True
    return None


def build_deck(spec) -> dict | None:
    ids = []
    unresolved = []
    for name, copies in spec["cards"].items():
        cid = resolve(name)
        if cid is None:
            unresolved.append(name)
            continue
        card = BY_ID[cid]
        maxc = 1 if card["rarity"] == "LEGENDARY" else 2
        for _ in range(min(copies, maxc)):
            ids.append(cid)
    # Fill any remaining slots with class/neutral staples (respecting copy limits).
    from collections import Counter

    counts = Counter(ids)
    pool = [c for c in CARDS if c["cardClass"] in (spec["hero_class"], "NEUTRAL")]
    for c in pool:
        if len(ids) >= 30:
            break
        maxc = 1 if c["rarity"] == "LEGENDARY" else 2
        while counts[c["id"]] < maxc and len(ids) < 30:
            ids.append(c["id"])
            counts[c["id"]] += 1
    if unresolved:
        print(f"  [{spec['name']}] unresolved (filled): {unresolved}")
    return {"name": spec["name"], "hero_class": spec["hero_class"], "card_ids": ids, "tips": spec["tips"]}


def main():
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "frontend", "src", "data", "recommended_decks.json")
    decks = [build_deck(s) for s in DECKS]
    json.dump(decks, open(out, "w"), indent=1)
    print(f"Wrote {len(decks)} decks to {out}")
    for d in decks:
        print(f"  {d['name']}: {len(d['card_ids'])} cards")


if __name__ == "__main__":
    main()
