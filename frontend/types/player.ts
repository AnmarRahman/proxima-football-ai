// /types/player.ts

export interface Team {
  id: number;
  name: string;
  logo: string;
}

export interface GamesStats {
  position: string;
  rating?: number;
}

export interface Statistics {
  team: Team;
  games: GamesStats;
  goals?: {
    total?: number;
    assists?: number;
  };
}

export interface Player {
  player: any;
  id: string;
  name: string;
  firstname?: string;
  lastname?: string;
  age?: number;
  nationality?: string;
  birth_date?: string;
  height?: string;
  weight?: string;
  photo?: string;
  statistics: Statistics[];
}
