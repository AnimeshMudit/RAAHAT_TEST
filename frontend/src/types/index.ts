export interface UserSession {
  user_id: string;
  username: string;
  name: string;
  access_token?: string;
  refresh_token?: string;
}

export interface Message {
  id?: string;
  role: 'user' | 'ai' | 'raahat';
  content: string;
  timestamp?: string;
  isCrisis?: boolean;
}

export interface UserProfile {
  user_id?: string;
  username?: string;
  name?: string;
  display_name?: string;
  age?: number;
  reasons?: string[];
}

export interface SupabaseConfig {
  supabase_url: string;
  supabase_anon_key: string;
}
