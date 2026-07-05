import React, { createContext, useContext, useState, useCallback } from 'react';
import type { Message } from '../types';
import { apiFetch, getSupabaseClient, API_BASE } from '../services/api';
import { useAuth } from './AuthContext';

interface ChatContextType {
  messages: Message[];
  loadingHistory: boolean;
  sending: boolean;
  typing: boolean;
  crisisTriggered: boolean;
  welcomeBackBannerText: string | null;
  loadHistory: () => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  startNewChat: () => void;
  setCrisisTriggered: (val: boolean) => void;
  setWelcomeBackBannerText: (val: string | null) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [sending, setSending] = useState(false);
  const [typing, setTyping] = useState(false);
  const [crisisTriggered, setCrisisTriggered] = useState(false);
  const [welcomeBackBannerText, setWelcomeBackBannerText] = useState<string | null>(null);
  
  const { user, logout } = useAuth();

  const isCrisisResponse = (text: string): boolean => {
    const lower = text.toLowerCase();
    return (
      lower.includes('14416') ||
      lower.includes('icall') ||
      lower.includes('vandrevala') ||
      lower.includes('helpline')
    );
  };

  const loadHistory = useCallback(async () => {
    if (!user) return;
    setLoadingHistory(true);
    try {
      const data = await apiFetch('/api/history', { timeout: 20000 });
      const history = data.history || [];
      const formattedMessages: Message[] = history.map((m: any, index: number) => {
        const content = m.content || m.message || '';
        const role = m.role === 'ai' ? 'raahat' : 'user';
        return {
          id: `history-${index}`,
          role,
          content,
          isCrisis: role === 'raahat' && isCrisisResponse(content),
        };
      });

      if (formattedMessages.length > 0) {
        setWelcomeBackBannerText("Welcome back. I'm glad to see you again.");
        setMessages(formattedMessages);
      } else {
        setWelcomeBackBannerText(null);
        setMessages([]);
      }
    } catch (e: any) {
      console.warn('History load failed:', e);
      if (e.status === 401) {
        logout();
      } else {
        // Fallback or error notice (non-blocking)
        setMessages([
          {
            id: 'err-history',
            role: 'raahat',
            content: 'History is unavailable right now. You can still send a new message.',
          },
        ]);
      }
    } finally {
      setLoadingHistory(false);
    }
  }, [user, logout]);

  const sendMessage = async (text: string) => {
    if (!user || sending) return;
    const trimmed = text.trim();
    if (!trimmed) return;

    if (trimmed.length > 2000) {
      alert('Please keep messages under 2000 characters.');
      return;
    }

    setSending(true);
    setTyping(true);

    // Append User Message
    const userMsgId = `user-${Date.now()}`;
    const userMessage: Message = {
      id: userMsgId,
      role: 'user',
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMessage]);

    // Setup streaming placeholder message
    const streamMsgId = `ai-${Date.now()}`;
    let aiResponseText = '';

    try {
      const client = await getSupabaseClient();
      const sessionRes = await client.auth.getSession();
      const token = sessionRes.data?.session?.access_token || '';

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: trimmed,
          preferred_name: user.name || '',
        }),
      });

      if (!response.ok) {
        throw new Error(`Server responded with status ${response.status}`);
      }

      setTyping(false);

      // Append stream placeholder
      const placeholderMessage: Message = {
        id: streamMsgId,
        role: 'raahat',
        content: '',
      };
      setMessages((prev) => [...prev, placeholderMessage]);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      if (reader) {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep partial line in buffer

          for (const line of lines) {
            const cleanLine = line.trim();
            if (!cleanLine.startsWith('data: ')) continue;

            try {
              const parsed = JSON.parse(cleanLine.substring(6));
              if (parsed.text) {
                aiResponseText += parsed.text;
                // Update the placeholder message content
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === streamMsgId ? { ...msg, content: aiResponseText } : msg
                  )
                );
              } else if (parsed.error) {
                console.error('Stream error:', parsed.error);
              }
            } catch (e) {
              console.error('Failed to parse stream line:', cleanLine, e);
            }
          }
        }

        // Parse any remaining buffer
        if (buffer) {
          const cleanLine = buffer.trim();
          if (cleanLine.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(cleanLine.substring(6));
              if (parsed.text) {
                aiResponseText += parsed.text;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === streamMsgId ? { ...msg, content: aiResponseText } : msg
                  )
                );
              }
            } catch (e) {}
          }
        }
      }

      // Check if crisis was triggered in stream
      if (isCrisisResponse(aiResponseText)) {
        setCrisisTriggered(true);
        setMessages((prev) =>
          prev.map((msg) => (msg.id === streamMsgId ? { ...msg, isCrisis: true } : msg))
        );
      }
    } catch (streamError) {
      console.warn('Chat stream failed, falling back to standard POST:', streamError);
      
      try {
        // Fallback POST
        const result = await apiFetch('/api/chat', {
          method: 'POST',
          body: {
            message: trimmed,
            preferred_name: user.name || '',
          },
          timeout: 60000,
        });

        setTyping(false);
        const reply = result?.response || 'I am here with you.';
        const isCrisis = isCrisisResponse(reply);

        if (isCrisis) {
          setCrisisTriggered(true);
        }

        const fallbackAiMessage: Message = {
          id: `ai-post-${Date.now()}`,
          role: 'raahat',
          content: reply,
          isCrisis,
        };

        // Remove placeholder if it was added, otherwise just append
        setMessages((prev) => {
          const filtered = prev.filter((msg) => msg.id !== streamMsgId);
          return [...filtered, fallbackAiMessage];
        });
      } catch (fallbackError) {
        console.error('Fallback chat send failed:', fallbackError);
        setTyping(false);
        
        const errorMessage: Message = {
          id: `err-${Date.now()}`,
          role: 'raahat',
          content: 'Message could not be sent. Please check your connection and try again.',
        };
        
        setMessages((prev) => {
          const filtered = prev.filter((msg) => msg.id !== streamMsgId);
          return [...filtered, errorMessage];
        });
      }
    } finally {
      setSending(false);
      setTyping(false);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setWelcomeBackBannerText(null);
    setCrisisTriggered(false);
  };

  return (
    <ChatContext.Provider
      value={{
        messages,
        loadingHistory,
        sending,
        typing,
        crisisTriggered,
        welcomeBackBannerText,
        loadHistory,
        sendMessage,
        startNewChat,
        setCrisisTriggered,
        setWelcomeBackBannerText,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
};
export default ChatContext;
