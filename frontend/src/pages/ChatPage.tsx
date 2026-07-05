import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useChat } from '../context/ChatContext';
import { motion, AnimatePresence } from 'framer-motion';
import logoUrl from '../assets/raahat_light-removebg-preview.png';
import defaultAvatar from '../assets/default_avatar.png';

const ChatPage: React.FC = () => {
  const { user, updateName, logout, refreshProfile } = useAuth();
  const {
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
  } = useChat();

  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isInfoOpen, setIsInfoOpen] = useState(false);
  const [showNameModal, setShowNameModal] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [nameError, setNameError] = useState('');
  const [nameModalLoading, setNameModalLoading] = useState(false);
  
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);

  // 1. Initial Sync and History Load
  useEffect(() => {
    const initPage = async () => {
      // Sync user profile from server
      const profile = await refreshProfile();
      
      // If we don't have a preferred name, open the name input modal
      const hasName = user?.name || (profile && profile.name);
      if (!hasName) {
        setShowNameModal(true);
        setNameInput('');
      } else {
        setShowNameModal(false);
      }
      
      // Load history
      await loadHistory();
    };

    initPage();
  }, [loadHistory]);

  // 2. Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, typing]);

  // 3. Focus Name Input modal
  useEffect(() => {
    if (showNameModal) {
      setTimeout(() => nameInputRef.current?.focus(), 50);
    }
  }, [showNameModal]);

  // 4. Auto-resize textarea input
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (showNameModal) {
      if (e.key === 'Enter') e.preventDefault();
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = async () => {
    if (showNameModal || sending || !inputValue.trim()) return;
    const textToSend = inputValue;
    setInputValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    await sendMessage(textToSend);
  };

  const handleNameModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = nameInput.trim();
    if (!trimmed) {
      setNameError('Please enter your name.');
      nameInputRef.current?.focus();
      return;
    }

    setNameModalLoading(true);
    setNameError('');
    try {
      await updateName(trimmed);
      setShowNameModal(false);
    } catch (err: any) {
      console.error(err);
      setNameError(err.message || 'Unable to save your name.');
      nameInputRef.current?.focus();
    } finally {
      setNameModalLoading(false);
    }
  };

  // Traps focus inside the Name Modal
  const handleNameModalKeyDown = (e: React.KeyboardEvent) => {
    if (e.key !== 'Tab') return;
    const modal = document.getElementById('name-modal-box');
    if (!modal) return;
    const focusables = modal.querySelectorAll('input, button');
    const first = focusables[0] as HTMLElement;
    const last = focusables[focusables.length - 1] as HTMLElement;

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  const usePrompt = (text: string) => {
    if (showNameModal) return;
    setInputValue(text);
    textareaRef.current?.focus();
  };

  const formatText = (text: string) => {
    return text.split('\n').map((line, idx) => (
      <span key={idx}>
        {line}
        <br />
      </span>
    ));
  };

  const getUserDisplayName = () => {
    if (!user) return 'friend';
    const display = user.name || user.username;
    return display.includes('@') ? display.split('@')[0] : display;
  };



  return (
    <div className="h-screen w-screen flex bg-[#fdfcf9] text-[#1a2018] overflow-hidden font-sans relative">
      {/* ─── NAME OVERLAY MODAL ─── */}
      <AnimatePresence>
        {showNameModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-[#1a2018]/40 backdrop-blur-md"
            onKeyDown={handleNameModalKeyDown}
          >
            <motion.div
              id="name-modal-box"
              initial={{ scale: 0.9, y: 15 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 15 }}
              transition={{ type: 'spring', damping: 25, stiffness: 250 }}
              className="bg-white/95 border border-[#e8e0d0] rounded-3xl p-8 max-w-sm w-full mx-4 shadow-2xl flex flex-col items-center text-center"
              role="dialog"
              aria-modal="true"
            >
              <div className="w-14 h-14 rounded-2xl bg-[#e8f0eb] flex items-center justify-center mb-4">
                <img src={logoUrl} alt="Raahat Logo" className="w-10 h-10 object-contain" />
              </div>
              <h3 className="font-serif text-[#1a2018] text-xl font-medium mb-2">RAAHAT</h3>
              <p className="text-xs text-[#6b7a68] leading-relaxed mb-6 font-light">
                Before we begin, we'd love to know what to call you during our conversations.
              </p>

              <form onSubmit={handleNameModalSubmit} className="w-full flex flex-col items-start gap-2">
                <label className="text-[10px] font-semibold uppercase tracking-wider text-[#3d4a3a]" htmlFor="modal-name-input">
                  Your name
                </label>
                <input
                  ref={nameInputRef}
                  id="modal-name-input"
                  type="text"
                  placeholder="Enter your name"
                  value={nameInput}
                  onChange={(e) => {
                    setNameInput(e.target.value);
                    if (nameError) setNameError('');
                  }}
                  className={`w-full border rounded-xl px-4 py-3 text-sm text-[#1a2018] focus:border-[#4a7c59] focus:ring-2 focus:ring-[#e8f0eb] transition-all placeholder:text-[#9aaa97]/70 ${
                    nameError ? 'border-red-300 ring-1 ring-red-50' : 'border-[#e8e0d0]'
                  }`}
                  disabled={nameModalLoading}
                />
                {nameError && (
                  <span className="text-[11px] text-[#ba1a1a] mt-1 text-left" aria-live="polite">
                    {nameError}
                  </span>
                )}

                <button
                  type="submit"
                  disabled={nameModalLoading}
                  className="w-full bg-[#4a7c59] text-white py-3 rounded-full text-xs font-semibold uppercase tracking-wider hover:bg-[#2d5a54] active:scale-95 duration-200 shadow-sm mt-4 disabled:bg-gray-300"
                >
                  {nameModalLoading ? 'Saving...' : 'Continue'}
                </button>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── DESKTOP SIDEBAR ─── */}
      <aside className="hidden lg:flex w-[var(--sidebar-w)] h-full bg-[#f5f0e8] border-r border-[#e8e0d0] flex-col flex-shrink-0 z-30">
        <div className="p-6 border-b border-[#e8e0d0] flex flex-col items-center">
          <img src={logoUrl} alt="Raahat" className="w-[110px] h-[40px] object-contain mb-1" />
          <div className="text-[9px] font-sans font-light tracking-[0.08em] uppercase text-[#9aaa97] text-center">
            राहत · Your safe space
          </div>

          <button
            onClick={startNewChat}
            className="w-full mt-4 flex items-center justify-center gap-2 bg-[#4a7c59] hover:bg-[#2d5a54] text-white rounded-xl py-2.5 text-xs font-semibold transition-all shadow-sm duration-200"
          >
            <svg className="w-3.5 h-3.5 stroke-white fill-none stroke-2" viewBox="0 0 16 16">
              <line x1="8" y1="2" x2="8" y2="14" />
              <line x1="2" y1="8" x2="14" y2="8" />
            </svg>
            New conversation
          </button>
        </div>

        {/* History List */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9aaa97] px-2 mb-3">
            Recent
          </div>
          {messages.length > 0 ? (
            <div className="space-y-1">
              <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-[#e8f0eb] border border-[#4a7c59]/10 text-xs font-medium text-[#4a7c59] cursor-pointer">
                <svg className="w-3.5 h-3.5 stroke-[#4a7c59] fill-none stroke-[1.5]" viewBox="0 0 16 16">
                  <path d="M14 9.5A5.5 5.5 0 118.5 4H14v5.5z" />
                </svg>
                <span className="truncate flex-1">
                  {messages.find((m) => m.role === 'user')?.content || 'Current chat'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-[#9aaa97] italic px-2">No recent chats</div>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-[#e8e0d0] flex flex-col gap-3">
          <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-[#e8e0d0]/50 transition-colors cursor-pointer group">
            <div className="w-8 h-8 rounded-full overflow-hidden border border-[#2d5a54]/10 bg-white flex items-center justify-center text-xs font-semibold text-[#4a7c59]">
              <img src={defaultAvatar} alt="User initials" className="w-full h-full object-cover" />
            </div>
            <div className="truncate flex-grow">
              <div className="text-xs font-semibold text-[#1a2018] leading-tight truncate">
                {getUserDisplayName()}
              </div>
              <div className="text-[9px] text-[#9aaa97] truncate">
                {user?.username?.includes('@') ? user.username : ''}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => setIsInfoOpen(true)}
              className="flex items-center justify-center gap-1.5 border border-[#e8e0d0] hover:bg-white bg-white/40 text-xs font-medium py-2 rounded-xl text-[#3d4a3a] transition-all"
            >
              <svg className="w-3.5 h-3.5 stroke-[#6b7a68] fill-none stroke-[1.5]" viewBox="0 0 16 16">
                <circle cx="8" cy="8" r="6" />
                <line x1="8" y1="7" x2="8" y2="11" />
                <circle cx="8" cy="5" r="0.5" fill="currentColor" />
              </svg>
              About
            </button>
            <button
              onClick={logout}
              className="flex items-center justify-center gap-1.5 border border-[#e8e0d0] hover:bg-white bg-white/40 text-xs font-medium py-2 rounded-xl text-[#ba1a1a] transition-all"
            >
              <svg className="w-3.5 h-3.5 stroke-[#ba1a1a] fill-none stroke-[1.5] stroke-linejoin-round stroke-linecap-round" viewBox="0 0 16 16">
                <path d="M10 3h3a1 1 0 011 1v8a1 1 0 01-1 1h-3M6 11l-3-3 3-3M2 8h8" />
              </svg>
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* ─── MOBILE DRAWER SIDEBAR ─── */}
      <AnimatePresence>
        {isSidebarOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.3 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsSidebarOpen(false)}
              className="fixed inset-0 z-40 bg-black lg:hidden"
            />
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'tween', duration: 0.3 }}
              className="fixed top-0 bottom-0 left-0 z-50 w-[270px] bg-[#f5f0e8] border-r border-[#e8e0d0] flex flex-col lg:hidden"
            >
              <div className="p-6 border-b border-[#e8e0d0] flex flex-col items-center relative">
                <button
                  onClick={() => setIsSidebarOpen(false)}
                  className="absolute right-4 top-4 text-xl text-[#9aaa97] hover:text-[#6b7a68]"
                >
                  ×
                </button>
                <img src={logoUrl} alt="Raahat" className="w-[100px] h-[38px] object-contain mb-1" />
                <div className="text-[9px] font-sans font-light tracking-[0.08em] uppercase text-[#9aaa97]">
                  राहत · Your safe space
                </div>

                <button
                  onClick={() => {
                    startNewChat();
                    setIsSidebarOpen(false);
                  }}
                  className="w-full mt-4 flex items-center justify-center gap-2 bg-[#4a7c59] hover:bg-[#2d5a54] text-white rounded-xl py-2.5 text-xs font-semibold transition-all shadow-sm"
                >
                  <svg className="w-3.5 h-3.5 stroke-white fill-none stroke-2" viewBox="0 0 16 16">
                    <line x1="8" y1="2" x2="8" y2="14" />
                    <line x1="2" y1="8" x2="14" y2="8" />
                  </svg>
                  New conversation
                </button>
              </div>

              <div className="flex-1 overflow-y-auto px-4 py-6">
                <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9aaa97] px-2 mb-3">
                  Recent
                </div>
                {messages.length > 0 ? (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-[#e8f0eb] border border-[#4a7c59]/10 text-xs font-medium text-[#4a7c59]">
                      <svg className="w-3.5 h-3.5 stroke-[#4a7c59] fill-none stroke-[1.5]" viewBox="0 0 16 16">
                        <path d="M14 9.5A5.5 5.5 0 118.5 4H14v5.5z" />
                      </svg>
                      <span className="truncate flex-1">
                        {messages.find((m) => m.role === 'user')?.content || 'Current chat'}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="text-[11px] text-[#9aaa97] italic px-2">No recent chats</div>
                )}
              </div>

              <div className="p-4 border-t border-[#e8e0d0] flex flex-col gap-3">
                <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-[#e8e0d0]/50 transition-colors">
                  <div className="w-8 h-8 rounded-full overflow-hidden border border-[#2d5a54]/10 bg-white flex items-center justify-center text-xs font-semibold text-[#4a7c59]">
                    <img src={defaultAvatar} alt="User initials" className="w-full h-full object-cover" />
                  </div>
                  <div className="truncate flex-grow">
                    <div className="text-xs font-semibold text-[#1a2018] leading-tight truncate">
                      {getUserDisplayName()}
                    </div>
                    <div className="text-[9px] text-[#9aaa97] truncate">
                      {user?.username?.includes('@') ? user.username : ''}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => {
                      setIsInfoOpen(true);
                      setIsSidebarOpen(false);
                    }}
                    className="flex items-center justify-center gap-1.5 border border-[#e8e0d0] hover:bg-white bg-white/40 text-xs font-medium py-2 rounded-xl text-[#3d4a3a]"
                  >
                    About
                  </button>
                  <button
                    onClick={logout}
                    className="flex items-center justify-center gap-1.5 border border-[#e8e0d0] hover:bg-white bg-white/40 text-xs font-medium py-2 rounded-xl text-[#ba1a1a]"
                  >
                    Sign out
                  </button>
                </div>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* ─── MAIN CHAT AREA ─── */}
      <main className="flex-1 h-full flex flex-col min-w-0 bg-[#fdfcf9] relative z-10">
        
        {/* Top Header */}
        <header className="h-[70px] border-b border-[#2d5a54]/10 flex items-center justify-between px-4 md:px-8 bg-white/70 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-3">
            {/* Burger menu for mobile */}
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden text-[#3d4a3a] hover:text-[#4a7c59] text-2xl flex items-center justify-center pr-1"
            >
              <span className="material-symbols-outlined">menu</span>
            </button>

            <div className="w-9 h-9 rounded-full bg-[#E3DFF2]/35 flex items-center justify-center text-[#7C73A7]">
              <img src={logoUrl} alt="Raahat" className="w-[26px] h-[26px] object-contain" />
            </div>
            <div>
              <h1 className="font-serif text-[#1a2018] text-sm font-semibold tracking-tight leading-none">
                RAAHAT
              </h1>
              <div className="flex items-center gap-1.5 mt-1">
                <span className={`w-1.5 h-1.5 rounded-full inline-block ${typing || sending ? 'bg-orange-400 animate-pulse' : 'bg-green-500'}`} />
                <span className="text-[10px] text-[#6b7a68] font-medium">
                  {typing ? 'Thinking…' : sending ? 'Typing…' : 'Ready to listen'}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsInfoOpen((prev) => !prev)}
              className="w-8 h-8 rounded-full border border-[#e8e0d0] hover:bg-[#f5f0e8]/50 flex items-center justify-center transition-colors text-[#6b7a68] hover:text-[#3d4a3a]"
              title="Session info"
            >
              <span className="material-symbols-outlined text-[20px]">info</span>
            </button>
            <button
              onClick={startNewChat}
              className="w-8 h-8 rounded-full border border-[#e8e0d0] hover:bg-[#f5f0e8]/50 flex items-center justify-center transition-colors text-[#6b7a68] hover:text-[#3d4a3a]"
              title="New chat"
            >
              <span className="material-symbols-outlined text-[20px]">edit_square</span>
            </button>
          </div>
        </header>

        {/* Disclaimer Banner */}
        <div className="bg-[#f5f0e8]/80 px-4 py-2 border-b border-[#e8e0d0] text-[10px] md:text-xs text-[#6b7a68] flex items-center gap-2 font-light">
          <span className="material-symbols-outlined text-[15px] text-[#9aaa97] flex-shrink-0">info</span>
          RAAHAT provides emotional support and reflection tools. It is not a substitute for professional mental health care.
        </div>

        {/* Welcome Back Banner */}
        {welcomeBackBannerText && (
          <div className="bg-[#e8f0eb] border-b border-[#4a7c59]/10 px-4 py-2 text-xs text-[#2d5a54] font-medium flex items-center justify-between">
            <span>{welcomeBackBannerText}</span>
            <button onClick={() => setWelcomeBackBannerText(null)} className="text-sm font-semibold leading-none hover:text-black">
              ×
            </button>
          </div>
        )}

        {/* Messages Scrolling Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
          
          {loadingHistory ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <div className="w-6 h-6 border-2 border-[#4a7c59]/30 border-t-[#4a7c59] rounded-full animate-spin" />
              <span className="text-xs text-[#9aaa97] font-light">Loading conversations...</span>
            </div>
          ) : messages.length === 0 ? (
            /* Welcome Screen / Empty State */
            <div className="max-w-xl mx-auto flex flex-col items-center text-center py-10 md:py-16">
              <div className="w-16 h-16 rounded-full bg-[#E3DFF2]/20 flex items-center justify-center mb-5">
                <img src={logoUrl} alt="Raahat" className="w-11 h-11 object-contain" />
              </div>
              <h2 className="font-serif text-2xl md:text-3xl text-[#1a2018] font-normal tracking-tight">
                Hello, {getUserDisplayName()}
              </h2>
              <p className="text-sm text-[#6b7a68] font-light leading-relaxed max-w-sm mt-3 mb-8">
                This is your safe space. You can share anything — I won't judge. What's on your mind today?
              </p>

              {/* Suggestions chips */}
              <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                {[
                  "I've been feeling really low lately",
                  "I just needed somewhere to vent",
                  "I'm overthinking everything",
                  "I feel exhausted all the time",
                  "I can't sleep because of racing thoughts"
                ].map((prompt, index) => (
                  <button
                    key={index}
                    onClick={() => usePrompt(prompt)}
                    className="bg-[#faf9f6]/95 border border-[#e8e0d0] hover:border-[#7aab8a] hover:bg-[#e8f0eb]/20 text-[#3d4a3a] hover:text-[#4a7c59] text-xs px-4 py-2.5 rounded-full shadow-sm hover:shadow-md transition-all duration-200"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Message List */
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((msg, index) => {
                const isUser = msg.role === 'user';
                return (
                  <motion.div
                    key={msg.id || index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35 }}
                    className={`flex items-start gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}
                  >
                    {/* Avatar */}
                    {!isUser && (
                      <div className="w-8 h-8 rounded-full bg-[#E3DFF2]/35 flex-shrink-0 flex items-center justify-center text-xs mt-1">
                        <img src={logoUrl} alt="R" className="w-[18px] h-[18px] object-contain" />
                      </div>
                    )}

                    <div className={`flex flex-col max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
                      {/* Bubble */}
                      <div
                        className={`p-4 rounded-2xl shadow-sm text-sm leading-relaxed ${
                          msg.isCrisis
                            ? 'bg-[#faece7] border border-[#d85a30]/15 text-[#3d4a3a] rounded-bl-sm shadow-[0_4px_15px_rgba(216,90,48,0.06)]'
                            : isUser
                            ? 'bg-[#2d5a54] text-white rounded-br-sm shadow-[0_4px_15px_rgba(45,90,84,0.1)]'
                            : 'bg-white/95 border border-white/60 text-[#3d4a3a] rounded-bl-sm'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{formatText(msg.content)}</p>
                      </div>

                      {/* Meta information */}
                      <span className="text-[9px] text-[#9aaa97] font-medium tracking-wide mt-1.5 uppercase px-1">
                        {isUser ? 'You' : 'RAAHAT'}
                      </span>
                    </div>

                    {isUser && (
                      <div className="w-8 h-8 rounded-full overflow-hidden border border-[#2d5a54]/10 bg-white flex-shrink-0 mt-1 flex items-center justify-center">
                        <img src={defaultAvatar} alt="User Avatar" className="w-full h-full object-cover" />
                      </div>
                    )}
                  </motion.div>
                );
              })}

              {/* Typing Indicator */}
              {typing && (
                <div className="flex items-start gap-3.5 justify-start">
                  <div className="w-8 h-8 rounded-full bg-[#E3DFF2]/35 flex-shrink-0 flex items-center justify-center text-xs mt-1">
                    <img src={logoUrl} alt="R" className="w-[18px] h-[18px] object-contain" />
                  </div>
                  <div className="flex flex-col items-start max-w-[75%]">
                    <div className="bg-[#faf9f6]/80 border border-[#e8e0d0] p-4 rounded-2xl rounded-bl-sm flex gap-1.5 items-center shadow-inner">
                      <div className="w-1.5 h-1.5 bg-[#4a7c59]/60 rounded-full animate-bounce" />
                      <div className="w-1.5 h-1.5 bg-[#4a7c59]/60 rounded-full animate-bounce [animation-delay:150ms]" />
                      <div className="w-1.5 h-1.5 bg-[#4a7c59]/60 rounded-full animate-bounce [animation-delay:300ms]" />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Crisis Resource Bar */}
        <AnimatePresence>
          {crisisTriggered && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 15 }}
              className="bg-[#faece7] border-t border-[#d85a30]/15 px-4 py-3 text-xs md:text-sm text-[#3d4a3a] flex items-center justify-between gap-4 z-10"
            >
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[#d85a30] text-xl flex-shrink-0">warning</span>
                <p className="font-light">
                  If you're in crisis right now:{' '}
                  <strong className="text-[#d85a30] font-semibold">Kiran 14416</strong> ·{' '}
                  <strong className="text-[#d85a30] font-semibold">iCall 9152987821</strong> ·{' '}
                  <strong className="text-[#d85a30] font-semibold">Vandrevala 1860-266-2345</strong>
                </p>
              </div>
              <button
                onClick={() => setCrisisTriggered(false)}
                className="text-lg font-bold leading-none text-[#9aaa97] hover:text-[#d85a30] px-2 py-1"
                title="Dismiss"
              >
                ×
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat Input Box Area */}
        <footer className="p-4 md:p-6 bg-transparent relative z-10">
          <div className="max-w-3xl mx-auto flex flex-col gap-2">
            <div className="flex gap-2 items-center bg-[#faf9f6]/95 border border-[#e8e0d0] rounded-2xl px-4 py-3 shadow-[0_4px_20px_rgba(0,0,0,0.02)] focus-within:border-[#7aab8a] focus-within:shadow-[0_4px_25px_rgba(74,124,89,0.06)] transition-all">
              <textarea
                ref={textareaRef}
                rows={1}
                placeholder="Share what's on your mind…"
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                disabled={showNameModal || sending}
                className="flex-grow bg-transparent border-none resize-none outline-none text-sm text-[#151c27] placeholder-[#9aaa97]/70 py-1 max-h-[140px] focus:ring-0 focus:outline-none"
              />
              <button
                onClick={handleSend}
                disabled={showNameModal || sending || !inputValue.trim()}
                className="w-9 h-9 rounded-full bg-[#4a7c59] hover:bg-[#2d5a54] text-white flex items-center justify-center transition-all duration-200 active:scale-95 disabled:bg-[#c5d9ca] disabled:scale-100 flex-shrink-0"
                title="Send"
              >
                <svg className="w-4 h-4 stroke-white fill-none stroke-2 translate-x-[1px]" viewBox="0 0 17 17">
                  <path d="M14.5 8.5L2 3l2.5 5.5L2 14l12.5-5.5z" />
                </svg>
              </button>
            </div>
            <p className="text-[10px] text-[#9aaa97] text-center font-light leading-relaxed px-4">
              RAAHAT provides emotional support only · Not therapy or emergency care · For emergencies, contact Kiran Helpline 14416
            </p>
          </div>
        </footer>
      </main>

      {/* ─── SLIDE-OUT ABOUT INFO PANEL ─── */}
      <AnimatePresence>
        {isInfoOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.3 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsInfoOpen(false)}
              className="fixed inset-0 z-40 bg-black"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.3 }}
              className="fixed top-0 bottom-0 right-0 z-50 w-[300px] md:w-[340px] bg-white border-l border-[#e8e0d0] flex flex-col p-6 overflow-y-auto shadow-2xl space-y-6"
            >
              <div className="flex items-center justify-between border-b border-[#e8e0d0] pb-4">
                <span className="font-serif text-[#1a2018] text-base font-semibold">About RAAHAT</span>
                <button onClick={() => setIsInfoOpen(false)} className="text-2xl text-[#9aaa97] hover:text-[#3d4a3a] px-2 leading-none">
                  ×
                </button>
              </div>

              <div className="space-y-6 text-xs md:text-sm font-light text-[#6b7a68] leading-relaxed">
                <div>
                  <h4 className="font-semibold text-[#3d4a3a] uppercase tracking-wider text-[10px] mb-2">How RAAHAT works</h4>
                  <div className="bg-[#f5f0e8]/55 border border-[#e8e0d0] rounded-xl p-4">
                    Your messages are matched against clinical mental health resources (WHO stress workbooks, CBT, DBT, ACT, PFA manuals) to give you grounded, evidence-informed responses — not just generic advice.
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-[#3d4a3a] uppercase tracking-wider text-[10px] mb-2">Safety</h4>
                  <div className="bg-[#f5f0e8]/55 border border-[#e8e0d0] rounded-xl p-4">
                    RAAHAT has a built-in crisis detection layer. If your message contains signs of genuine distress, it will immediately surface helpline numbers. This cannot be turned off.
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-[#3d4a3a] uppercase tracking-wider text-[10px] mb-2">Emergency Helplines</h4>
                  <div className="bg-[#faece7] border border-[#d85a30]/15 rounded-xl p-4 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span>Kiran Mental Health</span>
                      <strong className="text-[#d85a30] font-mono">14416</strong>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span>iCall (TISS)</span>
                      <strong className="text-[#d85a30] font-mono">9152987821</strong>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span>Vandrevala Foundation</span>
                      <strong className="text-[#d85a30] font-mono">1860-266-2345</strong>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-[#3d4a3a] uppercase tracking-wider text-[10px] mb-2">Privacy</h4>
                  <div className="bg-[#f5f0e8]/55 border border-[#e8e0d0] rounded-xl p-4">
                    Conversations are stored securely in Supabase to provide continuity. Passwords are bcrypt-hashed. No data is ever sold or shared with third parties.
                  </div>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ChatPage;
