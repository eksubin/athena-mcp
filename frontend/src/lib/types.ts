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
  /** The listing itself. Present on summaries too, so a card can link out
   * without a second request per job. */
  url: string;
  source: string | null;
  location: string | null;
  salary_min: number | null;
  salary_max: number | null;
  remote: boolean;
  easy_apply: boolean;
  posted_at: string | null;
  score: number | null;
}

export interface Application {
  id: string;
  job_id: string;
  status: ApplicationStatus;
  notes: string | null;
  applied_at: string | null;
  updated_at: string;
  /** Embedded by the API in the same request — null only if the listing
   * was removed from the catalog. */
  job: JobSummary | null;
}

export interface Preferences {
  titles?: string[];
  remote_only?: boolean;
  salary_min?: number;
}

export type AccountRole = "member" | "admin";

/** The five faces in components/avatar.tsx. The database stores the key. */
export type AvatarName = "fox" | "owl" | "cat" | "bear" | "fawn";

export interface Profile {
  id: string;
  username: string;
  avatar_seed: string;
  avatar: AvatarName;
  real_name: string | null;
  preferences: Preferences;
  role: AccountRole;
  /** How many live invites this account may hold. Admins ignore it. */
  invite_limit: number;
  disabled_at: string | null;
}

export interface Invite {
  id: string;
  email: string;
  role: AccountRole;
  note: string | null;
  created_at: string;
  revoked_at: string | null;
  accepted_at: string | null;
  accepted_user_id: string | null;
}

export interface AdminInvite extends Invite {
  invited_by: string | null;
  invited_by_username: string | null;
  accepted_username: string | null;
}

export interface AdminAccount {
  id: string;
  username: string;
  email: string;
  real_name: string | null;
  avatar: AvatarName;
  role: AccountRole;
  disabled_at: string | null;
  invite_limit: number;
  invites_used: number;
  application_count: number;
  created_at: string;
  last_sign_in_at: string | null;
}

export interface AdminOverview {
  members: number;
  admins: number;
  disabled: number;
  pending_invites: number;
}

export interface ProfileFact {
  key: string;
  value: string;
  confidence: number;
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
  avatar: AvatarName;
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
