export interface CardMeta {
  id: string;
  name: string;
  text?: string;
  cost: number | null;
  attack: number | null;
  health: number | null;
  type: string;
  cardClass: string;
  rarity: string;
  set: string;
  collectible?: boolean;
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
}

export interface Deck {
  id: number;
  user_id: number;
  name: string;
  hero_class: string;
  card_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface GameCard {
  entity_id: number;
  id?: string;
  name?: string;
  cost?: number;
  text?: string;
  atk?: number;
  max_health?: number;
  damage?: number;
  armor?: number;
  taunt?: boolean;
  stealthed?: boolean;
  divine_shield?: boolean;
  frozen?: boolean;
  exhausted?: boolean;
  num_attacks?: number;
  can_attack?: boolean;
  attack_targets?: number[];
  requires_target?: boolean;
  targets?: number[];
  zone_position?: number;
  zone?: number;
}

export interface GamePlayer {
  index: number;
  hero: GameCard;
  hero_power: GameCard | null;
  weapon: GameCard | null;
  deck_count: number;
  hand: GameCard[];
  field: GameCard[];
  secrets: GameCard[];
  max_mana: number;
  mana: number;
  playstate: string;
}

export interface GameState {
  turn: number;
  current_player: number;
  ended: boolean;
  result: { winner: number | null; playstates: string[] } | null;
  players: [GamePlayer, GamePlayer];
  pending: { player: number; kind: string } | null;
}
