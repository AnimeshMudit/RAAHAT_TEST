import { createClient, SupabaseClient } from '@supabase/supabase-js';

const IS_DEV_SERVER = (
  typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname === '') &&
  window.location.port !== '8000'
);

export const API_BASE = IS_DEV_SERVER ? 'http://127.0.0.1:8000' : (typeof window !== 'undefined' ? window.location.origin : '');

export const SESSION_KEY = 'raahat_user';

let supabaseClient: SupabaseClient | null = null;
let configPromise: Promise<{ supabase_url: string; supabase_anon_key: string }> | null = null;

export async function fetchConfig() {
  if (!configPromise) {
    configPromise = apiFetch<{ supabase_url: string; supabase_anon_key: string }>('/api/config')
      .then((config) => {
        // Expose to window if any external script relies on it (preserving compatibility)
        if (typeof window !== 'undefined') {
          (window as any).SUPABASE_URL = config.supabase_url;
          (window as any).SUPABASE_ANON_KEY = config.supabase_anon_key;
        }
        return config;
      })
      .catch((err) => {
        console.error('Failed to fetch Supabase config:', err);
        configPromise = null;
        throw err;
      });
  }
  return configPromise;
}

export async function getSupabaseClient(): Promise<SupabaseClient> {
  if (supabaseClient) {
    return supabaseClient;
  }

  const config = await fetchConfig();
  if (!config.supabase_url || !config.supabase_anon_key) {
    throw new Error('Supabase configuration is missing from the server.');
  }

  supabaseClient = createClient(config.supabase_url, config.supabase_anon_key);

  try {
    const { data: activeSession } = await supabaseClient.auth.getSession();
    if (!activeSession?.session) {
      const localSession = loadSession();
      if (localSession && localSession.access_token) {
        await supabaseClient.auth.setSession({
          access_token: localSession.access_token,
          refresh_token: localSession.refresh_token || '',
        });
      }
    }
  } catch (err) {
    console.warn('Failed to sync session to Supabase Client:', err);
  }

  return supabaseClient;
}

export interface ApiFetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: any;
  timeout?: number;
}

export async function apiFetch<T = any>(
  path: string,
  { method = 'GET', body = null, timeout = 15000 }: ApiFetchOptions = {}
): Promise<T> {
  let token: string | null = null;
  if (path !== '/api/config' && path !== '/api/login' && path !== '/api/signup') {
    try {
      const client = await getSupabaseClient();
      const { data } = await client.auth.getSession();
      token = data?.session?.access_token || null;
    } catch (err) {
      console.warn('Could not fetch token for API request:', err);
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  const options: RequestInit = {
    method,
    headers: {
      Accept: 'application/json',
    },
    signal: controller.signal,
  };

  if (token) {
    (options.headers as any)['Authorization'] = `Bearer ${token}`;
  }

  if (body !== null) {
    (options.headers as any)['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  return fetch(API_BASE + path, options)
    .then(async (response) => {
      clearTimeout(timeoutId);
      const rawText = await response.text();
      let parsed: any = null;
      if (rawText) {
        try {
          parsed = JSON.parse(rawText);
        } catch (_error) {
          parsed = null;
        }
      }
      if (!response.ok) {
        const message =
          (parsed && (parsed.detail || parsed.message || parsed.error)) ||
          response.statusText ||
          'Request failed';
        const error = new Error(message) as any;
        error.status = response.status;
        error.body = parsed;
        throw error;
      }
      return parsed;
    })
    .catch((error) => {
      if (error && error.name === 'AbortError') {
        throw new Error('Request timed out. Please try again.');
      }
      throw error;
    });
}

export function saveSession(user: any) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(user));
  if (user && user.user_id) {
    localStorage.setItem('raahat_user_id', user.user_id);
  }
}

export function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (_error) {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem('raahat_user_id');
}
