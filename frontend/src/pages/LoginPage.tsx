import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import logoUrl from '../assets/raahat_light-removebg-preview.png';

const LoginPage: React.FC = () => {
  const { user, login, signup, signInWithGoogle, completeOAuth } = useAuth();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  
  const [statusMessage, setStatusMessage] = useState<{ text: string; isError: boolean } | null>(null);
  const [buttonLoading, setButtonLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState(false);

  // Check for OAuth parameters on mount
  useEffect(() => {
    const handleOAuthCallback = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const errorDescription = params.get('error_description') || params.get('error');
      const hasHashToken = window.location.hash.includes('access_token=');

      if (code || errorDescription || hasHashToken) {
        setOauthLoading(true);
        setStatusMessage({ text: 'Completing sign-in with Google...', isError: false });
        try {
          const handled = await completeOAuth();
          if (handled) {
            console.log('Google Auth completed successfully.');
          }
        } catch (error: any) {
          console.error('OAuth callback processing failed:', error);
          setStatusMessage({
            text: error.message || 'Google sign-in failed. Please try again.',
            isError: true,
          });
        } finally {
          setOauthLoading(false);
        }
      } else {
        // If user is already logged in, redirect to chat
        if (user) {
          if (!user.name || !user.name.trim()) {
            navigate('/onboarding');
          } else {
            navigate('/chat');
          }
        }
      }
    };

    handleOAuthCallback();
  }, [user, completeOAuth, navigate]);

  const emailLooksValid = (addr: string) => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(addr || '').trim());
  };

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage(null);

    const trimmedEmail = email.trim();
    if (!emailLooksValid(trimmedEmail)) {
      setStatusMessage({ text: 'Enter a valid email address.', isError: true });
      return;
    }

    if (!password) {
      setStatusMessage({ text: 'Enter your password.', isError: true });
      return;
    }

    setButtonLoading(true);
    try {
      await login(trimmedEmail, password);
    } catch (err: any) {
      console.error('Login failed:', err);
      setStatusMessage({
        text: err.message || 'Login failed. Please verify your credentials.',
        isError: true,
      });
    } finally {
      setButtonLoading(false);
    }
  };

  const handleSignupSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatusMessage(null);

    const trimmedEmail = signupEmail.trim();
    if (!emailLooksValid(trimmedEmail)) {
      setStatusMessage({ text: 'Enter a valid email address.', isError: true });
      return;
    }

    if (signupPassword.length < 8) {
      setStatusMessage({ text: 'Password must be at least 8 characters.', isError: true });
      return;
    }

    setButtonLoading(true);
    try {
      await signup(trimmedEmail, signupPassword);
    } catch (err: any) {
      console.error('Signup failed:', err);
      setStatusMessage({
        text: err.message || 'Signup failed. Please try again.',
        isError: true,
      });
    } finally {
      setButtonLoading(false);
    }
  };

  const handleGoogleClick = async () => {
    setStatusMessage(null);
    setOauthLoading(true);
    try {
      await signInWithGoogle();
    } catch (err: any) {
      console.error('Google Sign In failed:', err);
      setStatusMessage({
        text: err.message || 'Google sign-in could not be initiated.',
        isError: true,
      });
      setOauthLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fdfcf9] flex flex-col justify-center items-center p-6 relative overflow-hidden select-none">
      {/* Decorative blurs */}
      <div className="absolute top-[-10%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-[#e8f0eb] opacity-70 blur-[100px] pointer-events-none" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-[#f5e8d5] opacity-60 blur-[100px] pointer-events-none" />

      {/* Main Container */}
      <motion.div 
        initial={{ opacity: 0, y: 25 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative z-10"
      >
        {/* Branding header */}
        <div className="text-center mb-8 flex flex-col items-center">
          <img src={logoUrl} alt="RAAHAT" className="w-[130px] h-[50px] object-contain mb-2" />
          <h2 className="font-serif text-[#1a2018] text-2xl font-normal leading-none tracking-tight">RAAHAT</h2>
          <span className="text-[11px] font-sans font-light tracking-[0.1em] uppercase text-[#9aaa97] mt-1.5">
            राहत · Your Mental Health Companion
          </span>
        </div>

        {/* Auth Glass Card */}
        <div className="glass-card bg-white/40 border border-white/60 backdrop-blur-xl rounded-[28px] p-6 md:p-8 shadow-2xl relative overflow-hidden">
          {/* Tab Selector */}
          <div className="flex gap-2 mb-6 p-1 bg-[#f5f0e8]/50 rounded-full border border-[#e8e0d0]/50">
            <button
              type="button"
              onClick={() => {
                setActiveTab('login');
                setStatusMessage(null);
              }}
              className={`flex-1 rounded-full py-2.5 text-xs font-semibold uppercase tracking-wider transition-all duration-300 ${
                activeTab === 'login'
                  ? 'bg-[#2d5a54] text-white shadow-sm'
                  : 'text-[#2d5a54] hover:bg-[#f5f0e8] hover:text-[#1a2018]'
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab('signup');
                setStatusMessage(null);
              }}
              className={`flex-1 rounded-full py-2.5 text-xs font-semibold uppercase tracking-wider transition-all duration-300 ${
                activeTab === 'signup'
                  ? 'bg-[#2d5a54] text-white shadow-sm'
                  : 'text-[#2d5a54] hover:bg-[#f5f0e8] hover:text-[#1a2018]'
              }`}
            >
              Sign Up
            </button>
          </div>

          {/* Status Message */}
          <AnimatePresence mode="wait">
            {statusMessage && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className={`mb-6 rounded-xl border px-4 py-3 text-xs font-medium ${
                  statusMessage.isError
                    ? 'border-red-200 bg-red-50 text-red-700'
                    : 'border-[#2d5a54]/10 bg-[#e8f0eb] text-[#2d5a54]'
                }`}
              >
                {statusMessage.text}
              </motion.div>
            )}
          </AnimatePresence>

          {/* FORMS */}
          <div className="relative">
            {activeTab === 'login' ? (
              <motion.form
                key="login-form"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                onSubmit={handleLoginSubmit}
                className="space-y-4"
              >
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#3d4a3a] mb-2" htmlFor="email">
                    Email Address
                  </label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-[#9aaa97] text-xl pointer-events-none">
                      mail
                    </span>
                    <input
                      type="email"
                      id="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-white/70 border border-[#c0c8c6] rounded-xl pl-10 pr-4 py-3 text-sm text-[#151c27] focus:border-[#7C73A7] focus:ring-2 focus:ring-[#E3DFF2] transition-all placeholder:text-[#9aaa97]/70 shadow-sm"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#3d4a3a] mb-2" htmlFor="password">
                    Password
                  </label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-[#9aaa97] text-xl pointer-events-none">
                      lock
                    </span>
                    <input
                      type="password"
                      id="password"
                      placeholder="Enter your password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full bg-white/70 border border-[#c0c8c6] rounded-xl pl-10 pr-4 py-3 text-sm text-[#151c27] focus:border-[#7C73A7] focus:ring-2 focus:ring-[#E3DFF2] transition-all placeholder:text-[#9aaa97]/70 shadow-sm"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={buttonLoading || oauthLoading}
                  className="w-full bg-[#7C73A7] text-white py-3 rounded-full text-sm font-semibold hover:bg-[#2d5a54] shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-0.5 disabled:bg-gray-300 disabled:transform-none disabled:shadow-none"
                >
                  {buttonLoading ? 'Signing in...' : 'Sign In'}
                </button>
              </motion.form>
            ) : (
              <motion.form
                key="signup-form"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                onSubmit={handleSignupSubmit}
                className="space-y-4"
              >
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#3d4a3a] mb-2" htmlFor="signup-email">
                    Email Address
                  </label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-[#9aaa97] text-xl pointer-events-none">
                      mail
                    </span>
                    <input
                      type="email"
                      id="signup-email"
                      placeholder="you@example.com"
                      value={signupEmail}
                      onChange={(e) => setSignupEmail(e.target.value)}
                      className="w-full bg-white/70 border border-[#c0c8c6] rounded-xl pl-10 pr-4 py-3 text-sm text-[#151c27] focus:border-[#7C73A7] focus:ring-2 focus:ring-[#E3DFF2] transition-all placeholder:text-[#9aaa97]/70 shadow-sm"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#3d4a3a] mb-2" htmlFor="signup-password">
                    Password
                  </label>
                  <div className="relative">
                    <span className="material-symbols-outlined absolute left-3 top-1/2 transform -translate-y-1/2 text-[#9aaa97] text-xl pointer-events-none">
                      lock
                    </span>
                    <input
                      type="password"
                      id="signup-password"
                      placeholder="Create a strong password (min 8 chars)"
                      value={signupPassword}
                      onChange={(e) => setSignupPassword(e.target.value)}
                      className="w-full bg-white/70 border border-[#c0c8c6] rounded-xl pl-10 pr-4 py-3 text-sm text-[#151c27] focus:border-[#7C73A7] focus:ring-2 focus:ring-[#E3DFF2] transition-all placeholder:text-[#9aaa97]/70 shadow-sm"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={buttonLoading || oauthLoading}
                  className="w-full bg-[#7C73A7] text-white py-3 rounded-full text-sm font-semibold hover:bg-[#2d5a54] shadow-md hover:shadow-lg transition-all duration-300 transform hover:-translate-y-0.5 disabled:bg-gray-300 disabled:transform-none disabled:shadow-none"
                >
                  {buttonLoading ? 'Creating account...' : 'Create Account'}
                </button>
              </motion.form>
            )}
          </div>

          {/* Divider */}
          <div className="relative flex py-5 items-center">
            <div className="flex-grow border-t border-[#e8e0d0]"></div>
            <span className="flex-shrink mx-4 text-xs text-[#9aaa97] uppercase tracking-widest font-semibold">
              or
            </span>
            <div className="flex-grow border-t border-[#e8e0d0]"></div>
          </div>

          {/* OAuth Buttons */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={handleGoogleClick}
              disabled={buttonLoading || oauthLoading}
              className="w-full border border-[#c0c8c6] bg-white/80 hover:bg-[#fdfcf9] hover:border-[#7C73A7]/50 text-[#3d4a3a] py-3 rounded-full text-sm font-medium flex items-center justify-center gap-3 transition-all duration-200 active:scale-95 disabled:bg-gray-50 disabled:border-gray-200 disabled:text-gray-400 disabled:transform-none"
            >
              <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              Continue with Google
            </button>
          </div>
        </div>

        {/* Legal Disclaimer / Footer */}
        <p className="text-center text-[10px] text-[#9aaa97] mt-6 leading-relaxed max-w-xs mx-auto">
          RAAHAT is a supportive companion, not a medical or diagnostic service. By signing in, you agree to prioritize your well-being.
        </p>
      </motion.div>
    </div>
  );
};

export default LoginPage;
