import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import type { UserSession, UserProfile } from '../types';
import {
  apiFetch,
  saveSession as saveLocalSession,
  loadSession as loadLocalSession,
  clearSession as clearLocalSession,
  getSupabaseClient,
} from '../services/api';

interface AuthContextType {
  user: UserSession | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
  signInWithGoogle: () => Promise<void>;
  completeOAuth: () => Promise<boolean>;
  updateName: (name: string) => Promise<void>;
  updateProfile: (displayName: string, age: number, reasons: string[]) => Promise<void>;
  refreshProfile: () => Promise<UserProfile | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserSession | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  // On mount, load session from localStorage and restore from Supabase if needed
  useEffect(() => {
    const initSession = async () => {
      const local = loadLocalSession();
      if (local) {
        setUser(local);
      }
      
      // Wait for OAuth handlers to complete first
      const hasOAuthParams =
        window.location.search.includes('code=') ||
        window.location.search.includes('error=') ||
        window.location.hash.includes('access_token=');
        
      if (!hasOAuthParams) {
        try {
          const restored = await restoreSessionFromSupabase();
          if (restored) {
            setUser(restored);
          }
        } catch (e) {
          console.warn('Initial session restore skipped:', e);
        }
      }
      setLoading(false);
    };
    initSession();
  }, []);

  const restoreSessionFromSupabase = async (): Promise<UserSession | null> => {
    try {
      const client = await getSupabaseClient();
      const { data, error } = await client.auth.getSession();
      const session = data?.session;
      const email = session?.user?.email;

      if (error || !email) {
        return null;
      }

      try {
        const syncResult = await apiFetch('/api/sync-user', {
          method: 'POST',
          body: {},
          timeout: 20000,
        });

        if (syncResult?.user_id) {
          const sessionRecord: UserSession = {
            user_id: syncResult.user_id,
            username: syncResult.username || email,
            name: syncResult.name || '',
            access_token: session?.access_token,
            refresh_token: session?.refresh_token,
          };
          saveLocalSession(sessionRecord);
          return sessionRecord;
        }
      } catch (syncError) {
        console.error('Supabase session sync failed:', syncError);
      }
    } catch (restoreError) {
      console.error('Supabase restore failed:', restoreError);
    }
    return null;
  };

  const login = async (email: string, password: string) => {
    const result = await apiFetch('/api/login', {
      method: 'POST',
      body: { username: email, password },
      timeout: 20000,
    });
    if (result && result.user_id) {
      const sessionRecord: UserSession = {
        user_id: result.user_id,
        username: result.username || email,
        name: result.name || '',
        access_token: result.session?.access_token,
        refresh_token: result.session?.refresh_token,
      };
      saveLocalSession(sessionRecord);
      setUser(sessionRecord);

      if (result.is_new_signup) {
        navigate('/onboarding');
      } else {
        navigate('/chat');
      }
    } else {
      throw new Error('Login succeeded but no session was returned.');
    }
  };

  const signup = async (email: string, password: string) => {
    const result = await apiFetch('/api/signup', {
      method: 'POST',
      body: { username: email, password },
      timeout: 25000,
    });
    if (result && result.user_id) {
      const sessionRecord: UserSession = {
        user_id: result.user_id,
        username: result.username || email,
        name: result.name || '',
        access_token: result.session?.access_token,
        refresh_token: result.session?.refresh_token,
      };
      saveLocalSession(sessionRecord);
      setUser(sessionRecord);

      if (result.is_new_signup) {
        navigate('/onboarding');
      } else {
        navigate('/chat');
      }
    }
  };

  const logout = () => {
    clearLocalSession();
    setUser(null);
    // Also clear other Supabase localStorage keys
    if (typeof localStorage !== 'undefined') {
      const keysToRemove: string[] = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('sb-')) {
          keysToRemove.push(key);
        }
      }
      keysToRemove.forEach((k) => localStorage.removeItem(k));
    }
    navigate('/login');
  };

  const signInWithGoogle = async () => {
    try {
      const client = await getSupabaseClient();
      const redirectTo = `${window.location.origin}/auth/callback`;
      const { error } = await client.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo,
        },
      });
      if (error) throw error;
    } catch (error) {
      console.error('Google auth failed:', error);
      throw error;
    }
  };

  const completeOAuth = async (): Promise<boolean> => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const errorDescription = params.get('error_description') || params.get('error');
    const hasHashToken = window.location.hash.includes('access_token=');

    if (!code && !errorDescription && !hasHashToken) {
      return false;
    }

    if (errorDescription) {
      throw new Error(errorDescription);
    }

    try {
      const client = await getSupabaseClient();
      
      if (code) {
        const { error } = await client.auth.exchangeCodeForSession(code);
        if (error) throw error;
      } else if (hasHashToken) {
        const { data, error } = await client.auth.getSession();
        if (error) throw error;
        if (!data.session) {
          throw new Error('Supabase session not established from hash.');
        }
      }

      const sessionRes = await client.auth.getSession();
      const session = sessionRes.data?.session;
      const email = session?.user?.email || session?.user?.user_metadata?.email;
      
      if (!email) {
        throw new Error('Google sign-in did not return an email address.');
      }

      const syncResult = await apiFetch('/api/sync-user', {
        method: 'POST',
        body: {},
        timeout: 20000,
      });

      if (!syncResult?.user_id) {
        throw new Error('Unable to create a local session.');
      }

      const sessionRecord: UserSession = {
        user_id: syncResult.user_id,
        username: syncResult.username || email,
        name: syncResult.name || '',
        access_token: session?.access_token,
        refresh_token: session?.refresh_token,
      };
      
      saveLocalSession(sessionRecord);
      setUser(sessionRecord);

      // Clean up URL search and hash
      const url = new URL(window.location.href);
      url.search = '';
      url.hash = '';
      window.history.replaceState({}, document.title, url.pathname + url.search);

      // Wait a tiny bit and navigate
      await new Promise((resolve) => setTimeout(resolve, 300));
      if (syncResult.is_new_signup || syncResult.needs_name) {
        navigate('/onboarding');
      } else {
        navigate('/chat');
      }
      return true;
    } catch (error) {
      // Clean up URL search and hash on error as well
      const url = new URL(window.location.href);
      url.search = '';
      url.hash = '';
      window.history.replaceState({}, document.title, url.pathname + url.search);
      throw error;
    }
  };

  const updateName = async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) {
      throw new Error('Please enter your name.');
    }

    await apiFetch('/api/user-name', {
      method: 'POST',
      body: { name: trimmed },
    });

    if (user) {
      const updated = { ...user, name: trimmed };
      saveLocalSession(updated);
      setUser(updated);
    }
  };

  const updateProfile = async (displayName: string, age: number, reasons: string[]) => {
    // Save to localStorage (per specifications)
    localStorage.setItem('raahat_display_name', displayName);
    localStorage.setItem('raahat_age', age.toString());
    localStorage.setItem('raahat_reasons', JSON.stringify(reasons));

    try {
      await apiFetch('/api/update-profile', {
        method: 'POST',
        body: { display_name: displayName, age },
      });
    } catch (e) {
      console.warn('Profile update failed:', e);
    }

    if (user) {
      const updated = { ...user, name: displayName };
      saveLocalSession(updated);
      setUser(updated);
    }
  };

  const refreshProfile = async (): Promise<UserProfile | null> => {
    if (!user) return null;
    try {
      const data = await apiFetch<UserProfile>('/api/user-profile');
      const profileName = String(data?.name || data?.display_name || '').trim();
      if (profileName && user.name !== profileName) {
        const updated = { ...user, name: profileName };
        saveLocalSession(updated);
        setUser(updated);
      }
      return data;
    } catch (err: any) {
      if (err.status === 400 || err.status === 404 || err.status === 401) {
        logout();
      }
      return null;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        signup,
        logout,
        signInWithGoogle,
        completeOAuth,
        updateName,
        updateProfile,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
