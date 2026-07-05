import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import type { UserSession } from '../types';
import { SESSION_KEY } from '../services/api';

const QUOTES: Record<number, string> = {
  1: '"You don\'t have to have it all figured out to take the next step."',
  2: '"Knowing yourself is the beginning of all wisdom."',
  3: '"You took the first step. That already took courage."',
};

const REASONS = [
  { val: 'anxiety', label: 'Anxiety or worry', emoji: '😰' },
  { val: 'low', label: 'Feeling low', emoji: '🌧' },
  { val: 'stress', label: 'Stress', emoji: '🔥' },
  { val: 'lonely', label: 'Loneliness', emoji: '🌑' },
  { val: 'sleep', label: 'Sleep problems', emoji: '😴' },
  { val: 'vent', label: 'Just need to vent', emoji: '💬' },
  { val: 'explore', label: 'Just exploring', emoji: '🔍' },
  { val: 'academic', label: 'Academic pressure', emoji: '📚' },
];

const REASON_LABELS: Record<string, string> = {
  anxiety: '😰 Anxiety or worry',
  low: '🌧 Feeling low',
  stress: '🔥 Stress',
  lonely: '🌑 Loneliness',
  sleep: '😴 Sleep problems',
  vent: '💬 Need to vent',
  explore: '🔍 Exploring',
  academic: '📚 Academic pressure',
};

const OnboardingPage: React.FC = () => {
  const { updateProfile } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [age, setAge] = useState<number>(22);
  const [selectedReasons, setSelectedReasons] = useState<string[]>([]);
  const [nameError, setNameError] = useState('');
  const [ageError, setAgeError] = useState('');

  // Prefill name if already stored in localStorage
  useEffect(() => {
    if (typeof localStorage !== 'undefined') {
      const storedName = localStorage.getItem('raahat_display_name') || '';
      if (storedName) {
        setName(storedName);
      }
    }
  }, []);

  const handleStep1Submit = () => {
    if (!name.trim()) {
      setNameError('Please enter a name so RAAHAT knows what to call you.');
      return;
    }
    setNameError('');
    setStep(2);
  };

  const syncAgeSlider = (val: string) => {
    const parsed = parseInt(val, 10);
    if (!isNaN(parsed)) {
      setAge(parsed);
    }
  };

  const handleStep2Submit = async (isSkip = false) => {
    if (!isSkip && (age < 13 || age > 80)) {
      setAgeError('Please enter a valid age between 13 and 80.');
      return;
    }
    setAgeError('');

    const finalAge = isSkip ? 22 : age;
    const finalReasons = isSkip ? [] : selectedReasons;

    try {
      await updateProfile(name, finalAge, finalReasons);
      setStep(3);
    } catch (err) {
      console.error('Failed to complete onboarding profile update:', err);
      // Even if network fails, proceed to step 3 per the original script behavior (non-blocking)
      setStep(3);
    }
  };

  const toggleReason = (val: string) => {
    setSelectedReasons((prev) =>
      prev.includes(val) ? prev.filter((r) => r !== val) : [...prev, val]
    );
  };

  const handleStartVenting = () => {
    try {
      const rawUser = localStorage.getItem(SESSION_KEY);
      if (rawUser) {
        const session: UserSession = JSON.parse(rawUser);
        session.name = name;
        localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      }
    } catch (e) {
      console.error('Failed to update session name:', e);
    }
    // Spec maps dashboard and chat to same page
    navigate('/chat');
  };

  return (
    <div className="min-h-screen grid grid-cols-1 md:grid-cols-2 bg-[#fdfcf9] text-[#1a2018]">
      {/* ─── LEFT PANEL (PROGRESS & BRANDING) ─── */}
      <aside className="bg-[#4a7c59] p-8 md:p-12 flex flex-col justify-between relative overflow-hidden text-white min-h-[30vh] md:min-h-screen">
        {/* Decorative background circles */}
        <div className="absolute w-[420px] h-[420px] rounded-full bg-white/[0.04] -top-[100px] -right-[100px] pointer-events-none" />
        <div className="absolute w-[280px] h-[280px] rounded-full bg-white/[0.04] -bottom-[60px] -left-[60px] pointer-events-none" />

        <div className="font-serif text-xl md:text-2xl font-medium tracking-tight relative z-10">
          RAAHAT
          <span className="block text-[10px] font-sans font-light tracking-[0.1em] uppercase text-white/60 mt-1">
            राहत · Mental Health Companion
          </span>
        </div>

        <div className="hidden md:block my-auto relative z-10 max-w-sm">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.4 }}
              className="font-serif text-2xl lg:text-3xl italic leading-relaxed text-white/95 mb-4"
            >
              {QUOTES[step] || QUOTES[1]}
            </motion.div>
          </AnimatePresence>
          <div className="text-xs font-light text-white/50 tracking-wider">
            — Setting up your safe space
          </div>
        </div>

        {/* Steps Indicators */}
        <div className="flex flex-row md:flex-col gap-4 md:gap-6 mt-6 md:mt-0 relative z-10">
          {[
            { num: 1, label: 'Your name' },
            { num: 2, label: 'About you' },
            { num: 3, label: 'All set' },
          ].map((s) => {
            const isActive = step === s.num;
            const isDone = step > s.num;
            return (
              <div
                key={s.num}
                className={`flex items-center gap-3 transition-opacity duration-300 ${
                  isActive ? 'opacity-100' : isDone ? 'opacity-70' : 'opacity-40'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full border-1.5 flex items-center justify-center text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-white border-white text-[#4a7c59] font-bold scale-110 shadow-sm'
                      : isDone
                      ? 'bg-white/20 border-white/50 text-white'
                      : 'border-white/35 text-white/60'
                  }`}
                >
                  {s.num}
                </div>
                <div className="hidden md:block text-sm font-light text-white/90">
                  {s.label}
                </div>
              </div>
            );
          })}
        </div>
      </aside>

      {/* ─── RIGHT PANEL (SCREENS) ─── */}
      <main className="p-8 md:p-16 flex flex-col justify-center items-center overflow-y-auto">
        <div className="max-w-md w-full">
          <AnimatePresence mode="wait">
            {/* STEP 1: Name */}
            {step === 1 && (
              <motion.div
                key="step-1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.4 }}
                className="flex flex-col"
              >
                <span className="text-[10px] font-semibold text-[#4a7c59] tracking-widest uppercase mb-2">
                  Step 1 of 2
                </span>
                <h1 className="font-serif text-3xl md:text-4xl font-normal text-[#1a2018] tracking-tight leading-snug mb-3">
                  What should <br />
                  RAAHAT <em className="text-[#4a7c59] not-italic">call you?</em>
                </h1>
                <p className="text-[#6b7a68] text-sm font-light leading-relaxed mb-8">
                  This is just your display name — RAAHAT will use it to feel more personal. No last name needed.
                </p>

                <div className="flex flex-col gap-2 mb-6">
                  <label className="text-xs font-semibold text-[#3d4a3a] uppercase tracking-wider" htmlFor="input-name">
                    Your name or nickname
                  </label>
                  <input
                    id="input-name"
                    type="text"
                    placeholder="e.g. Animesh, Anu, just me…"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      if (nameError) setNameError('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleStep1Submit();
                    }}
                    className={`w-full bg-white border rounded-xl px-4 py-3.5 text-sm text-[#1a2018] focus:border-[#4a7c59] focus:ring-2 focus:ring-[#e8f0eb] transition-all placeholder:text-[#9aaa97]/70 shadow-sm ${
                      nameError ? 'border-red-300 ring-2 ring-red-50' : 'border-[#e8e0d0]'
                    }`}
                  />
                  {nameError && <span className="text-xs text-[#ba1a1a] mt-1">{nameError}</span>}
                  <span className="text-[11px] text-[#9aaa97] font-light mt-1">This won't be shared with anyone.</span>
                </div>

                <button
                  type="button"
                  onClick={handleStep1Submit}
                  className="bg-[#4a7c59] text-white py-3.5 rounded-xl font-medium text-sm hover:bg-[#2d5a54] transition-all flex items-center justify-center gap-2 group hover:shadow-lg active:scale-95 duration-200"
                >
                  Continue
                  <svg className="w-4 h-4 stroke-white stroke-2 fill-none transform group-hover:translate-x-1 transition-transform" viewBox="0 0 16 16">
                    <path d="M3 8h10M9 4l4 4-4 4" />
                  </svg>
                </button>

                <div className="mt-8 pt-6 border-t border-[#e8e0d0] text-[10px] text-[#9aaa97] font-light text-center leading-relaxed">
                  RAAHAT is a digital sanctuary for emotional support. It does not provide therapy, clinical advice, or emergency medical services. If you are in crisis or immediate danger, please contact local emergency services or the Kiran Helpline at 14416.
                </div>
              </motion.div>
            )}

            {/* STEP 2: Age + context */}
            {step === 2 && (
              <motion.div
                key="step-2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.4 }}
                className="flex flex-col"
              >
                <span className="text-[10px] font-semibold text-[#4a7c59] tracking-widest uppercase mb-2">
                  Step 2 of 2
                </span>
                <h1 className="font-serif text-3xl md:text-4xl font-normal text-[#1a2018] tracking-tight leading-snug mb-3">
                  A little more <br />
                  <em className="text-[#4a7c59] not-italic">about you</em>
                </h1>
                <p className="text-[#6b7a68] text-sm font-light leading-relaxed mb-6">
                  Helps RAAHAT understand where you're coming from. All optional — share only what feels comfortable.
                </p>

                {/* Age Input */}
                <div className="flex flex-col gap-2 mb-6">
                  <label className="text-xs font-semibold text-[#3d4a3a] uppercase tracking-wider">
                    How old are you?
                  </label>
                  <div className="flex items-center gap-4">
                    <input
                      type="number"
                      min={13}
                      max={80}
                      value={age}
                      onChange={(e) => syncAgeSlider(e.target.value)}
                      className="w-20 text-center font-serif text-xl font-medium text-[#4a7c59] bg-white border border-[#e8e0d0] rounded-xl py-2 focus:border-[#4a7c59] focus:ring-2 focus:ring-[#e8f0eb] outline-none"
                    />
                    <div className="flex-1 flex flex-col gap-1.5">
                      <input
                        type="range"
                        min={13}
                        max={80}
                        value={age}
                        onChange={(e) => setAge(parseInt(e.target.value, 10))}
                        className="w-full h-1 bg-[#e8e0d0] rounded-lg appearance-none cursor-pointer accent-[#4a7c59]"
                      />
                      <div className="flex justify-between text-[10px] text-[#9aaa97] font-mono">
                        <span>13</span>
                        <span>80</span>
                      </div>
                    </div>
                  </div>
                  {ageError && <span className="text-xs text-[#ba1a1a] mt-1">{ageError}</span>}
                </div>

                {/* Reasons Checkboxes */}
                <div className="flex flex-col gap-2 mb-6">
                  <label className="text-xs font-semibold text-[#3d4a3a] uppercase tracking-wider mb-1">
                    What brings you to RAAHAT?{' '}
                    <span className="font-light text-[#9aaa97] lowercase">(pick all that feel right)</span>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {REASONS.map((r) => {
                      const isSelected = selectedReasons.includes(r.val);
                      return (
                        <button
                          key={r.val}
                          type="button"
                          onClick={() => toggleReason(r.val)}
                          className={`flex items-center gap-1.5 px-4 py-2 border rounded-full text-xs font-medium transition-all ${
                            isSelected
                              ? 'bg-[#e8f0eb] border-[#4a7c59] text-[#4a7c59] font-semibold'
                              : 'bg-white border-[#e8e0d0] text-[#3d4a3a] hover:bg-[#e8f0eb]/50 hover:border-[#7aab8a]'
                          }`}
                        >
                          <span>{r.emoji}</span> {r.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Actions */}
                <div className="space-y-3">
                  <button
                    type="button"
                    onClick={() => handleStep2Submit(false)}
                    className="w-full bg-[#4a7c59] text-white py-3.5 rounded-xl font-medium text-sm hover:bg-[#2d5a54] transition-all flex items-center justify-center gap-2 group hover:shadow-lg active:scale-95 duration-200"
                  >
                    Set up my space
                    <svg className="w-4 h-4 stroke-white stroke-2 fill-none transform group-hover:translate-x-1 transition-transform" viewBox="0 0 16 16">
                      <path d="M3 8h10M9 4l4 4-4 4" />
                    </svg>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleStep2Submit(true)}
                    className="w-full bg-transparent hover:bg-[#f5f0e8]/50 text-[#9aaa97] hover:text-[#6b7a68] py-2 rounded-xl text-xs transition-colors text-center"
                  >
                    Skip for now
                  </button>
                </div>

                <div className="mt-8 pt-6 border-t border-[#e8e0d0] text-[10px] text-[#9aaa97] font-light text-center leading-relaxed">
                  RAAHAT is a digital sanctuary for emotional support. It does not provide therapy, clinical advice, or emergency medical services. If you are in crisis or immediate danger, please contact local emergency services or the Kiran Helpline at 14416.
                </div>
              </motion.div>
            )}

            {/* STEP 3: Done */}
            {step === 3 && (
              <motion.div
                key="step-3"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.4 }}
                className="flex flex-col items-center text-center"
              >
                {/* Check Animation Ring */}
                <div className="w-20 h-20 rounded-full bg-[#e8f0eb] flex items-center justify-center mb-6 shadow-sm">
                  <svg className="w-10 h-10 stroke-[#4a7c59] stroke-2 fill-none stroke-linecap-round stroke-linejoin-round" viewBox="0 0 36 36">
                    <polyline points="6 18 14 26 30 10" className="animate-[drawCheck_0.6s_ease_both_delay-200ms]" />
                  </svg>
                </div>

                <h2 className="font-serif text-3xl font-normal text-[#1a2018] tracking-tight leading-snug mb-3">
                  Your space is <br />
                  <em className="text-[#4a7c59] not-italic">ready, {name || 'friend'}</em>
                </h2>
                <p className="text-[#6b7a68] text-sm font-light leading-relaxed max-w-xs mb-8">
                  RAAHAT remembers who you are and what matters to you. This conversation belongs to you.
                </p>

                {/* Summary Cards */}
                <div className="flex flex-col gap-3 w-full max-w-[340px] mb-8">
                  <div className="flex items-center gap-4 bg-[#e8f0eb] rounded-xl px-4 py-3 border border-[#4a7c59]/10 text-left shadow-sm">
                    <div className="text-lg flex-shrink-0">👤</div>
                    <div>
                      <div className="text-[10px] text-[#9aaa97] uppercase tracking-wider font-semibold">Name</div>
                      <div className="text-sm font-medium text-[#1a2018]">{name}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 bg-[#e8f0eb] rounded-xl px-4 py-3 border border-[#4a7c59]/10 text-left shadow-sm">
                    <div className="text-lg flex-shrink-0">🎂</div>
                    <div>
                      <div className="text-[10px] text-[#9aaa97] uppercase tracking-wider font-semibold">Age</div>
                      <div className="text-sm font-medium text-[#1a2018]">{age} years old</div>
                    </div>
                  </div>

                  {selectedReasons.length > 0 && (
                    <div className="flex items-center gap-4 bg-[#e8f0eb] rounded-xl px-4 py-3 border border-[#4a7c59]/10 text-left shadow-sm">
                      <div className="text-lg flex-shrink-0">🌿</div>
                      <div>
                        <div className="text-[10px] text-[#9aaa97] uppercase tracking-wider font-semibold">Here for</div>
                        <div className="text-sm font-medium text-[#1a2018] leading-tight">
                          {selectedReasons.map((r) => REASON_LABELS[r] || r).join(' · ')}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleStartVenting}
                  className="w-full max-w-[340px] bg-[#4a7c59] text-white py-3.5 rounded-xl font-medium text-sm hover:bg-[#2d5a54] transition-all flex items-center justify-center gap-2 group hover:shadow-lg active:scale-95 duration-200"
                >
                  Start talking to RAAHAT
                  <svg className="w-4 h-4 stroke-white stroke-2 fill-none transform group-hover:translate-x-1 transition-transform" viewBox="0 0 16 16">
                    <path d="M3 8h10M9 4l4 4-4 4" />
                  </svg>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
};

export default OnboardingPage;
