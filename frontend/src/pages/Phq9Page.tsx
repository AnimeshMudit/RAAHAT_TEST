import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { submitPhq9, getPhq9History } from '../services/phq9';
import { Phq9Result } from '../components/Phq9Result';
import type { Phq9Submission, Phq9HistoryEntry } from '../types';
import logoUrl from '../assets/raahat_light-removebg-preview.png';

const QUESTIONS = [
  "Little interest or pleasure in doing things",
  "Feeling down, depressed, or hopeless",
  "Trouble falling/staying asleep, or sleeping too much",
  "Feeling tired or having little energy",
  "Poor appetite or overeating",
  "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
  "Trouble concentrating on things, such as reading the newspaper or watching television",
  "Moving or speaking so slowly that other people could have noticed — or the opposite, being so fidgety or restless that you have been moving around a lot more than usual",
  "Thoughts that you would be better off dead, or of hurting yourself in some way"
];

const OPTIONS = [
  { label: "Not at all", value: 0 },
  { label: "Several days", value: 1 },
  { label: "More than half the days", value: 2 },
  { label: "Nearly every day", value: 3 }
];

export const Phq9Page: React.FC = () => {
  const navigate = useNavigate();

  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<Phq9Submission | null>(null);
  const [history, setHistory] = useState<Phq9HistoryEntry[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Clear errors on answer changes
  useEffect(() => {
    if (errorMessage) setErrorMessage(null);
  }, [answers]);

  const handleSelectAnswer = (qIdx: number, value: number) => {
    setAnswers((prev) => ({
      ...prev,
      [qIdx]: value
    }));
  };

  const isAllAnswered = () => {
    return QUESTIONS.every((_, idx) => answers[idx] !== undefined);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAllAnswered() || submitting) return;

    setSubmitting(true);
    setErrorMessage(null);

    const responsesArray = QUESTIONS.map((_, idx) => answers[idx]);

    try {
      const submissionResult = await submitPhq9(responsesArray);
      
      // Update history in parallel
      try {
        const historyData = await getPhq9History();
        setHistory(historyData);
      } catch (historyErr) {
        console.warn("Failed to load phq9 history data", historyErr);
      }

      setResult(submissionResult);
    } catch (err: any) {
      console.error("Submission failed:", err);
      if (err.status === 429) {
        setErrorMessage("You've recently taken this check-in. Please wait a minute before trying again.");
      } else if (err.status === 400 && err.body?.detail) {
        setErrorMessage(err.body.detail);
      } else {
        setErrorMessage("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetry = () => {
    setAnswers({});
    setResult(null);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-[#fdfcf9] text-[#1a2018] py-12 px-4 md:px-8 relative overflow-y-auto selection:bg-[#c5d9ca] selection:text-[#2d5a54]">
      {/* Decorative blurs */}
      <div className="absolute top-[-10%] left-[-15%] w-[45vw] h-[45vw] rounded-full bg-[#e8f0eb] opacity-60 blur-[110px] pointer-events-none" />
      <div className="absolute bottom-[10%] right-[-15%] w-[40vw] h-[40vw] rounded-full bg-[#f5e8d5] opacity-50 blur-[100px] pointer-events-none" />

      <div className="max-w-2xl mx-auto relative z-10">
        
        {/* Header/Branding */}
        {!result && (
          <div className="text-center mb-8 flex flex-col items-center">
            <img src={logoUrl} alt="Raahat" className="w-12 h-12 object-contain mb-3" />
            <h1 className="font-serif text-[#1a2018] text-2xl font-normal tracking-tight">Mood Check-in</h1>
            <p className="text-xs font-sans font-light tracking-[0.08em] uppercase text-[#9aaa97] mt-1.5">
              राहत · Reflect on how you've been feeling
            </p>
          </div>
        )}

        {/* Dynamic Display: Question Form OR Result Panel */}
        <AnimatePresence mode="wait">
          {result ? (
            <motion.div
              key="result"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5 }}
            >
              <Phq9Result submission={result} history={history} />
            </motion.div>
          ) : (
            <motion.div
              key="questions"
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -15 }}
              transition={{ duration: 0.5 }}
            >
              <div className="glass-card bg-white/40 border border-white/60 backdrop-blur-xl rounded-[28px] p-6 md:p-8 shadow-2xl">
                
                {/* Intro Line */}
                <div className="bg-[#faf9f6]/90 border border-[#e8e0d0] rounded-2xl p-4 md:p-5 mb-8 text-center text-xs md:text-sm text-[#3d4a3a] leading-relaxed shadow-sm font-light">
                  Over the last 2 weeks, how often have you been bothered by any of the following problems?
                </div>

                {/* Error Box */}
                {errorMessage && (
                  <div className="mb-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-xs md:text-sm text-red-700 font-medium flex items-center justify-between gap-4">
                    <span>{errorMessage}</span>
                    {errorMessage === "Something went wrong. Please try again." && (
                      <button
                        onClick={handleRetry}
                        type="button"
                        className="underline text-xs font-semibold hover:text-red-900 flex-shrink-0"
                      >
                        Reset form
                      </button>
                    )}
                  </div>
                )}

                {/* Questions list */}
                <form onSubmit={handleSubmit} className="space-y-8">
                  {QUESTIONS.map((qText, qIdx) => {
                    const selectedVal = answers[qIdx];
                    const showQ9Warning = qIdx === 8 && selectedVal !== undefined && selectedVal > 0;

                    return (
                      <div key={qIdx} className="border-b border-[#e8e0d0]/60 pb-6 last:border-b-0 last:pb-0 flex flex-col gap-4">
                        <div className="flex gap-3">
                          <span className="font-serif italic text-sm text-[#c5d9ca] font-normal leading-none pt-1">
                            {String(qIdx + 1).padStart(2, '0')}
                          </span>
                          <p className="text-sm md:text-base text-[#1a2018] font-light leading-relaxed">
                            {qText}
                          </p>
                        </div>

                        {/* Options */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          {OPTIONS.map((opt) => {
                            const isChecked = selectedVal === opt.value;
                            return (
                              <button
                                key={opt.value}
                                type="button"
                                onClick={() => handleSelectAnswer(qIdx, opt.value)}
                                className={`px-3 py-2.5 border rounded-xl text-xs text-center transition-all ${
                                  isChecked
                                    ? 'bg-[#2d5a54] border-[#2d5a54] text-white font-medium shadow-sm'
                                    : 'bg-white/80 border-[#e8e0d0] text-[#3d4a3a] hover:bg-[#e8f0eb]/30 hover:border-[#7aab8a]'
                                }`}
                              >
                                {opt.label}
                              </button>
                            );
                          })}
                        </div>

                        {/* Question 9 Crisis warning */}
                        {showQ9Warning && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            className="bg-[#faece7] border border-[#d85a30]/20 rounded-xl p-3 text-[11px] md:text-xs text-[#d85a30] leading-relaxed flex items-start gap-2.5"
                          >
                            <span className="material-symbols-outlined text-base flex-shrink-0">warning</span>
                            <p className="font-light">
                              Thank you for sharing that. If you're in crisis, RAAHAT has shared helpline numbers with you in chat — please reach out. You're not alone.
                            </p>
                          </motion.div>
                        )}
                      </div>
                    );
                  })}

                  {/* Submit and Navigation Actions */}
                  <div className="pt-6 border-t border-[#e8e0d0] flex flex-col sm:flex-row gap-3">
                    <button
                      type="submit"
                      disabled={!isAllAnswered() || submitting}
                      className="flex-grow bg-[#4a7c59] hover:bg-[#2d5a54] text-white py-3.5 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center justify-center gap-2 transition-all duration-200 active:scale-95 disabled:bg-gray-300 disabled:scale-100 shadow-sm"
                    >
                      {submitting ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Submitting...
                        </>
                      ) : (
                        "Submit check-in"
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate('/chat')}
                      className="sm:w-36 bg-transparent hover:bg-[#f5f0e8]/50 border border-[#e8e0d0] text-[#6b7a68] py-3.5 rounded-full text-xs font-semibold uppercase tracking-wider transition-colors text-center"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default Phq9Page;
