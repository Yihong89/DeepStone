/** Keyword reference shown in the hover popup. */
export const KEYWORD_DEFS: Record<string, string> = {
  "Battlecry": "Triggers when you play this card from your hand.",
  "Deathrattle": "Triggers when this minion dies.",
  "Taunt": "Enemies must attack this minion first.",
  "Charge": "Can attack the turn it is played.",
  "Rush": "Can attack enemy minions the turn it is played (but not heroes).",
  "Divine Shield": "The first damage this minion would take is negated.",
  "Poisonous": "Any minion damaged by this minion is destroyed.",
  "Lifesteal": "Damage this deals also heals your hero by the same amount.",
  "Windfury": "Can attack twice each turn.",
  "Stealth": "Can't be attacked or targeted by enemies until it attacks.",
  "Discover": "Choose one of three cards to add to your hand.",
  "Freeze": "Frozen characters can't attack on their next turn.",
  "Overload": "You have that many fewer mana crystals on your next turn.",
  "Combo": "A bonus effect if you played another card earlier this turn.",
  "Inspire": "Triggers whenever you use your Hero Power.",
  "Echo": "This card copies itself into your hand whenever you play it.",
  "Recruit": "Summon a random minion from your deck.",
  "Enrage": "While this minion is damaged, its effect is active.",
  "Reborn": "The first time this dies, it returns with 1 Health.",
  "Quest": "A card that rewards you when its objective is completed.",
  "Secret": "A hidden spell that triggers when its condition is met.",
  "Choose One": "Pick one of two effects when you play it.",
  "Adapt": "Choose one of three random upgrades when played.",
  "Magnetic": "Playing this next to a Mech merges it and grants its stats/effects.",
  "Spell Damage": "Your spells deal that much extra damage.",
  "Windfury (multi)": "Can attack multiple times each turn.",
  "Mega-Windfury": "Can attack four times each turn.",
};

/** Return the keyword names present in a card's text. */
export function getKeywords(text: string | undefined): string[] {
  if (!text) return [];
  const lower = text.toLowerCase();
  return Object.keys(KEYWORD_DEFS).filter((name) => lower.includes(name.toLowerCase()));
}
