export type ApplicationStatus =
  | "saved"
  | "applied"
  | "pending"
  | "interview"
  | "offer"
  | "rejected";

export interface JobSummary {
  id: string;
  title: string;
  company: string;
  location: string | null;
  salary_min: number | null;
  salary_max: number | null;
  remote: boolean;
  easy_apply: boolean;
  score: number | null;
}

export interface Application {
  id: string;
  job_id: string;
  status: ApplicationStatus;
  notes: string | null;
  applied_at: string | null;
  updated_at: string;
}

export interface Preferences {
  titles?: string[];
  remote_only?: boolean;
  salary_min?: number;
}

export interface Profile {
  id: string;
  username: string;
  avatar_seed: string;
  real_name: string | null;
  preferences: Preferences;
}

export interface Answer {
  id: string;
  question: string;
  answer: string;
  sensitive: boolean;
  confirmed_at: string | null;
}

export interface AccessToken {
  id: string;
  label: string;
  created_at: string;
  last_used_at: string | null;
}

export interface AccessTokenCreated {
  id: string;
  label: string;
  token: string;
}

export type StructureType = "sapling" | "tree" | "house" | "landmark" | "stump";

export interface Plot {
  user_id: string;
  username: string;
  avatar_seed: string;
  origin_x: number;
  origin_y: number;
}

export interface Structure {
  id: string;
  user_id: string;
  type: StructureType;
  grid_x: number;
  grid_y: number;
}
