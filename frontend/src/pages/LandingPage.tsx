import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../context/AuthContext';
import logoUrl from '../assets/raahat_light-removebg-preview.png';

const LandingPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleStartVenting = (e: React.MouseEvent) => {
    e.preventDefault();
    if (user) {
      navigate('/chat');
    } else {
      navigate('/login');
    }
  };

  const handleScrollTo = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  return (
    <div className="min-h-screen bg-[#fdfcf9] text-[#1a2018] relative overflow-x-hidden selection:bg-[#c5d9ca] selection:text-[#2d5a54]">
      {/* Dynamic Ambient Background Blurs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-[#e8f0eb] opacity-60 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[20%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-[#f5e8d5] opacity-50 blur-[100px] pointer-events-none" />

      {/* Navigation Header */}
      <motion.nav 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.8 }}
        className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 md:px-12 backdrop-blur-xl bg-white/40 border-b border-[#2d5a54]/10"
      >
        <div className="flex flex-col items-start gap-1 font-serif font-medium leading-none tracking-tight">
          <Link to="/" className="inline-flex items-center">
            <img src={logoUrl} alt="RAAHAT" className="w-[110px] h-[40px] object-contain" />
          </Link>
          <span className="text-[10px] font-sans font-light tracking-[0.08em] uppercase text-[#9aaa97] mt-0.5 ml-1">
            राहत · Mental Health Companion
          </span>
        </div>

        <ul className="hidden md:flex items-center gap-10 list-none">
          <li>
            <button onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} className="text-sm text-[#3d4a3a] hover:text-[#4a7c59] transition-colors">
              Home
            </button>
          </li>
          <li>
            <button onClick={() => handleScrollTo('how')} className="text-sm text-[#3d4a3a] hover:text-[#4a7c59] transition-colors">
              How it works
            </button>
          </li>
          <li>
            <button onClick={() => handleScrollTo('features')} className="text-sm text-[#3d4a3a] hover:text-[#4a7c59] transition-colors">
              Insights &amp; Features
            </button>
          </li>
          <li>
            <button onClick={() => handleScrollTo('safety')} className="text-sm text-[#3d4a3a] hover:text-[#4a7c59] transition-colors">
              Safety
            </button>
          </li>
        </ul>

        <div>
          <button
            onClick={handleStartVenting}
            className="bg-[#4a7c59] text-white px-5 py-2.5 rounded-full text-sm font-medium hover:bg-[#2d5a54] transition-all hover:shadow-[0_4px_15px_rgba(74,124,89,0.25)] hover:scale-105 duration-300 active:scale-95"
          >
            Start talking
          </button>
        </div>
      </motion.nav>

      {/* Hero Section */}
      <header className="max-w-[1200px] mx-auto min-h-screen grid grid-cols-1 lg:grid-cols-2 items-center px-6 md:px-12 pt-32 pb-16 gap-12 relative z-10">
        <motion.div 
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="flex flex-col items-start"
        >
          <div className="inline-flex items-center gap-2 bg-[#e8f0eb] text-[#4a7c59] text-xs font-semibold tracking-wider uppercase px-4 py-1.5 rounded-full mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4a7c59] animate-pulse" />
            Empathetic AI Companion
          </div>

          <h1 className="font-serif text-4xl md:text-6xl font-normal leading-[1.15] text-[#1a2018] tracking-tight mb-6">
            A companion for your <br />
            <em className="text-[#4a7c59] not-italic font-normal font-serif">emotional well-being.</em>
          </h1>

          <p className="text-base md:text-lg text-[#6b7a68] font-light leading-relaxed max-w-[480px] mb-10">
            RAAHAT is a private, evidence-grounded mental health companion. Talk through what you're feeling, resolve stress, and discover guided CBT tools — free from judgment.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
            <button
              onClick={handleStartVenting}
              className="bg-[#4a7c59] text-white px-8 py-3.5 rounded-full font-medium text-base hover:bg-[#2d5a54] transition-all shadow-[0_4px_20px_rgba(74,124,89,0.2)] hover:shadow-[0_8px_30px_rgba(74,124,89,0.3)] hover:-translate-y-0.5 active:translate-y-0 duration-300 text-center"
            >
              Start venting now
            </button>
            <button
              onClick={() => handleScrollTo('how')}
              className="inline-flex items-center justify-center gap-2 text-[#3d4a3a] border border-[#e8e0d0] px-6 py-3.5 rounded-full text-base hover:border-[#7aab8a] hover:text-[#4a7c59] bg-white/20 backdrop-blur-md transition-all duration-300"
            >
              See how it works
            </button>
          </div>
        </motion.div>

        {/* Hero Right: Chat Preview */}
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="relative"
        >
          {/* Glassmorphic Mock Chat Card */}
          <div className="glass-card p-6 md:p-8 rounded-[32px] max-w-[460px] mx-auto relative z-10 border border-white/40 shadow-2xl">
            <div className="flex items-center gap-3 pb-4 border-b border-[#e8e0d0] mb-6">
              <div className="w-10 h-10 rounded-full bg-[#7C73A7]/20 flex items-center justify-center text-[#7C73A7]">
                <img src={logoUrl} alt="R" className="w-6 h-6 object-contain" />
              </div>
              <div>
                <h4 className="font-serif text-[#1a2018] font-medium leading-none">RAAHAT</h4>
                <p className="text-xs text-[#6b7a68] mt-1 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#4a7c59] inline-block" /> Ready to listen
                </p>
              </div>
            </div>

            <div className="space-y-4 max-h-[300px] overflow-y-auto mb-6 pr-2">
              <div className="flex justify-end">
                <div className="max-w-[80%] bg-[#2d5a54] text-white px-4 py-3 rounded-2xl rounded-tr-sm shadow-sm text-sm leading-relaxed">
                  I can't seem to turn off my head tonight. I'm exhausted but my thoughts are just racing.
                </div>
              </div>

              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-full bg-[#7C73A7]/20 flex-shrink-0 flex items-center justify-center text-xs text-[#7C73A7]">
                  ✨
                </div>
                <div className="max-w-[80%] bg-white/70 backdrop-blur-md border border-white px-4 py-3 rounded-2xl rounded-tl-sm text-[#3d4a3a] text-sm leading-relaxed shadow-sm">
                  It's hard when your mind keeps running even when your body is tired. Let's take a slow breath together. Would you like to write down what's racing, or try a 2-minute centering exercise?
                </div>
              </div>
            </div>

            <div className="flex gap-2 items-center bg-[#faf9f6]/90 border border-[#e8e0d0] rounded-2xl px-4 py-3 shadow-inner">
              <span className="text-sm text-[#9aaa97] flex-1">Type what you feel...</span>
              <div className="w-8 h-8 rounded-full bg-[#4a7c59]/20 flex items-center justify-center text-white">
                <svg viewBox="0 0 16 16" className="w-4 h-4 fill-[#4a7c59]">
                  <path d="M14.5 8.5L2 3l2.5 5.5L2 14l12.5-5.5z" />
                </svg>
              </div>
            </div>
          </div>

          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[340px] h-[340px] rounded-full bg-[#e8f0eb] blur-[60px] z-0 pointer-events-none" />
        </motion.div>
      </header>

      {/* How it works Section */}
      <section id="how" className="py-24 bg-[#faf9f6]/70 border-y border-[#e8e0d0] relative z-10">
        <div className="max-w-[1200px] mx-auto px-6 md:px-12">
          <div className="text-center max-w-[600px] mx-auto mb-16">
            <p className="text-xs font-semibold tracking-widest text-[#4a7c59] uppercase mb-3">The process</p>
            <h2 className="font-serif text-3xl md:text-4xl font-normal tracking-tight text-[#1a2018] mb-4">
              More than a chatbot. <br />A structured listener.
            </h2>
            <p className="text-[#6b7a68] font-light text-sm md:text-base leading-relaxed">
              Every message goes through a three-step pipeline — emotion-aware, evidence-grounded, and always safe.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: 'You talk. RAAHAT listens.',
                desc: 'Before replying, RAAHAT runs a safety check. Crisis signals trigger immediate helpline resources. Casual language is never false-flagged — we understand the difference between "I\'m dying of laughter" and genuine distress.',
              },
              {
                step: '02',
                title: 'Context is retrieved.',
                desc: 'Your message generates semantic search keywords, which are matched against a FAISS vector store of WHO, CBT, DBT, ACT, and PFA clinical manuals. Only high-confidence matches inform the response.',
              },
              {
                step: '03',
                title: 'A grounded response.',
                desc: 'Llama 3.3-70B is guided by your conversation history and clinical context. It responds like a knowledgeable, warm friend — not a distant medical voice. Your history stays private, stored securely in Supabase.',
              },
            ].map((card, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: i * 0.15 }}
                className="glass-card hover:bg-white bg-white/30 border border-[#e8e0d0] hover:border-[#7aab8a] rounded-3xl p-8 hover:shadow-xl transition-all duration-300 flex flex-col gap-4 group"
              >
                <div className="text-3xl font-serif italic font-normal text-[#c5d9ca] group-hover:text-[#4a7c59] transition-colors duration-300">
                  {card.step}
                </div>
                <h3 className="font-serif text-xl font-normal text-[#1a2018]">{card.title}</h3>
                <p className="text-sm text-[#6b7a68] font-light leading-relaxed">{card.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 relative z-10">
        <div className="max-w-[1200px] mx-auto px-6 md:px-12">
          <div className="text-center max-w-[600px] mx-auto mb-16">
            <p className="text-xs font-semibold tracking-widest text-[#4a7c59] uppercase mb-3">What we built</p>
            <h2 className="font-serif text-3xl md:text-4xl font-normal tracking-tight text-[#1a2018] mb-4">
              Designed with care <br />at every layer.
            </h2>
            <p className="text-[#6b7a68] font-light text-sm md:text-base leading-relaxed">
              From crisis detection to hyperbole filtering — the thoughtful details behind RAAHAT.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {[
              {
                icon: '🛡️',
                title: 'Real crisis detection with nuance',
                desc: 'A deterministic safety layer scans for genuine distress signals — while a hyperbole filter prevents false alarms for idioms like "killing it" or "I\'m dead".',
              },
              {
                icon: '📖',
                title: 'Evidence-based RAG pipeline',
                desc: 'WHO stress workbooks, CBT group programs, DBT crisis skills, ACT workbooks, and PFA manuals — embedded and searched semantically for every conversation.',
              },
              {
                icon: '🧠',
                title: 'Persistent memory, no cold starts',
                desc: 'Each session builds on the last. RAAHAT remembers your name, your history, and your context — so you never have to start from zero.',
              },
              {
                icon: '💬',
                title: 'Three interfaces, one companion',
                desc: 'Talk via the web UI, through a CLI for developers, or on Telegram — the same RAAHAT everywhere, fitting into how you naturally reach for support.',
              },
              {
                icon: '🔑',
                title: 'Privacy-first architecture',
                desc: 'Passwords are bcrypt-hashed. All API keys are server-side only. Google OAuth support built in. No data ever leaves your session unencrypted.',
              },
              {
                icon: '🌿',
                title: 'Emotional energy matching',
                desc: 'High energy response when you celebrate wins. Soft, steady presence when you\'re low. RAAHAT reads your vibe and meets you there — not with a template.',
              },
            ].map((f, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="bg-white/40 border border-[#2d5a54]/5 rounded-2xl p-6 hover:bg-white/70 hover:shadow-lg transition-all duration-300 flex items-start gap-4"
              >
                <div className="w-12 h-12 rounded-xl bg-[#e8f0eb] flex items-center justify-center text-xl flex-shrink-0">
                  {f.icon}
                </div>
                <div>
                  <h4 className="font-serif text-[#1a2018] text-base font-medium mb-1.5">{f.title}</h4>
                  <p className="text-sm text-[#6b7a68] font-light leading-relaxed">{f.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Safety Section */}
      <section id="safety" className="py-24 bg-[#faf9f6]/90 border-t border-[#e8e0d0] relative z-10">
        <div className="max-w-[1200px] mx-auto px-6 md:px-12 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <p className="text-xs font-semibold tracking-widest text-[#4a7c59] uppercase mb-3">Not a replacement</p>
            <h2 className="font-serif text-3xl md:text-4xl font-normal tracking-tight text-[#1a2018] mb-6">
              We're a bridge, <br />not a destination.
            </h2>
            <p className="text-[#6b7a68] text-base font-light leading-relaxed mb-6 max-w-[460px]">
              RAAHAT is a first layer of support — available at 2am, on a rough Tuesday, between therapy sessions. It won't tell you everything is fine. It will tell you you're not alone.
            </p>
            <p className="text-sm text-[#9aaa97] font-light leading-relaxed max-w-[420px]">
              If you're in crisis, the safety system will always surface the right resources immediately — no matter what. This is not optional, and it never will be.
            </p>
          </div>

          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="bg-[#faece7] border border-[#d85a30]/15 rounded-3xl p-8 md:p-10 shadow-md"
          >
            <h3 className="font-serif text-[#d85a30] text-xl font-normal mb-4 flex items-center gap-2">
              ⚠️ Need immediate support?
            </h3>
            <p className="text-[#3d4a3a] text-sm leading-relaxed mb-6 font-light">
              RAAHAT automatically provides crisis resources when it detects genuine distress. These helplines are always available:
            </p>
            <div className="space-y-4">
              <div className="flex justify-between items-center bg-white/70 border border-[#d85a30]/10 rounded-xl px-5 py-3.5 shadow-sm">
                <span className="text-xs font-semibold tracking-wider uppercase text-[#6b7a68]">Kiran Mental Health Helpline</span>
                <strong className="text-base text-[#d85a30] font-mono">14416</strong>
              </div>
              <div className="flex justify-between items-center bg-white/70 border border-[#d85a30]/10 rounded-xl px-5 py-3.5 shadow-sm">
                <span className="text-xs font-semibold tracking-wider uppercase text-[#6b7a68]">iCall (TISS) Helpline</span>
                <strong className="text-base text-[#d85a30] font-mono">9152987821</strong>
              </div>
              <div className="flex justify-between items-center bg-white/70 border border-[#d85a30]/10 rounded-xl px-5 py-3.5 shadow-sm">
                <span className="text-xs font-semibold tracking-wider uppercase text-[#6b7a68]">Vandrevala Foundation</span>
                <strong className="text-base text-[#d85a30] font-mono">1860-266-2345</strong>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-[#1a2018] text-[#9aaa97] py-16 relative z-10 border-t border-[#3d4a3a]">
        <div className="max-w-[1200px] mx-auto px-6 md:px-12 flex flex-col md:flex-row justify-between gap-10 items-start">
          <div className="flex flex-col items-start gap-3">
            <div className="flex items-center gap-2">
              <img src={logoUrl} alt="RAAHAT Logo" className="w-[32px] h-[32px] object-contain invert opacity-80" />
              <span className="font-serif font-medium text-white text-lg tracking-tight">RAAHAT</span>
            </div>
            <div className="text-xs font-light mt-1">Built by Animesh Mudit &amp; Anshuman Awasthi</div>
          </div>
          <div className="text-xs md:text-sm font-light leading-relaxed max-w-[600px] text-[#6b7a68]">
            <strong className="text-white block mb-1">RAAHAT is not a licensed medical service.</strong>
            It is an AI companion tool and does not replace professional therapy, psychiatry, or emergency services. If you are in immediate danger, please call local emergency services or the Kiran Mental Health Helpline at 14416.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
