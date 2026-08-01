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
