import React from 'react';
import { useNavigate } from 'react-router-dom';
import type { Phq9Submission, Phq9HistoryEntry, Severity } from '../types';

interface Phq9ResultProps {
  submission: Phq9Submission;
  history: Phq9HistoryEntry[];
}

const SEVERITY_STYLES: Record<Severity, { text: string; bg: string; border: string }> = {
  "Minimal": { text: "text-[#2d5a54]", bg: "bg-[#e8f0eb]", border: "border-[#4a7c59]/20" },
  "Mild": { text: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  "Moderate": { text: "text-orange-700", bg: "bg-orange-50", border: "border-orange-200" },
  "Moderately Severe": { text: "text-[#d85a30]", bg: "bg-[#faece7]", border: "border-[#d85a30]/20" },
  "Severe": { text: "text-[#ba1a1a]", bg: "bg-red-50", border: "border-red-200" },
};

export const Phq9Result: React.FC<Phq9ResultProps> = ({ submission, history }) => {
  const navigate = useNavigate();
  const severityStyle = SEVERITY_STYLES[submission.severity] || SEVERITY_STYLES["Minimal"];

  // Sort history oldest to newest for chronological sparkline, capping at last 10 entries for display
  const sortedHistory = [...history]
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .slice(-10);

  // Sparkline coordinates calculator
  const renderSparkline = () => {
    if (sortedHistory.length < 2) return null;
    const width = 300;
    const height = 60;
    const padding = 10;
    
    const xStep = (width - padding * 2) / (sortedHistory.length - 1);
    const yScale = (height - padding * 2) / 27; // max score is 27

    const points = sortedHistory.map((item, idx) => {
      const x = padding + idx * xStep;
      const y = height - padding - item.score * yScale;
      return { x, y, score: item.score, date: new Date(item.timestamp).toLocaleDateString() };
    });

    const pathData = points.reduce((acc, p, idx) => {
      return idx === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
    }, "");

    return (
      <div className="flex flex-col items-center bg-[#faf9f6]/95 border border-[#e8e0d0] p-4 rounded-2xl shadow-inner mt-4 w-full">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-[#9aaa97] mb-2 self-start">
          Score Progress Trend
        </div>
        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
          {/* Grid lines */}
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#e8e0d0" strokeDasharray="3,3" />
          <line x1={padding} y1={height/2} x2={width - padding} y2={height/2} stroke="#e8e0d0" strokeDasharray="3,3" />
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#e8e0d0" />

          {/* Line Path */}
          <path d={pathData} fill="none" stroke="#4a7c59" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />

          {/* Dots */}
          {points.map((p, idx) => (
            <g key={idx} className="group cursor-pointer">
              <circle cx={p.x} cy={p.y} r="4.5" fill="#4a7c59" stroke="white" strokeWidth="1.5" />
              <title>{`Score: ${p.score} (${p.date})`}</title>
            </g>
          ))}
        </svg>
        <div className="flex justify-between w-full text-[10px] text-[#9aaa97] font-mono mt-2 px-1">
          <span>{new Date(sortedHistory[0].timestamp).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}</span>
          <span>{new Date(sortedHistory[sortedHistory.length - 1].timestamp).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}</span>
        </div>
      </div>
    );
  };

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Question 9 Safety Warning Banner */}
      {submission.q9_flag && (
        <div className="bg-[#faece7] border border-[#d85a30]/30 rounded-2xl p-4 text-xs md:text-sm text-[#d85a30] flex items-start gap-3 shadow-sm animate-pulse">
          <span className="material-symbols-outlined text-xl flex-shrink-0">warning</span>
          <p className="font-light leading-relaxed">
            Your response to question 9 suggests you may be in distress. Please consider reaching out to the crisis helplines RAAHAT has shared.
          </p>
        </div>
      )}

      {/* Main Result Card */}
      <div className="glass-card bg-white/40 border border-white/60 backdrop-blur-xl rounded-[28px] p-6 md:p-8 shadow-2xl flex flex-col items-center text-center">
        <span className="text-[10px] font-semibold text-[#4a7c59] tracking-widest uppercase mb-3">
          Check-in Complete
        </span>

        {/* Score Ring */}
        <div className={`w-24 h-24 rounded-full flex flex-col items-center justify-center border-2 ${severityStyle.border} ${severityStyle.bg} mb-5 shadow-sm`}>
          <span className="text-3xl font-serif font-medium text-[#1a2018] leading-none">{submission.score}</span>
          <span className="text-[10px] text-[#6b7a68] uppercase tracking-wider font-semibold mt-1">/ 27</span>
        </div>

        <h3 className="font-serif text-[#1a2018] text-xl font-normal mb-2 leading-none">
          Mood Check-in Result
        </h3>
        
        {/* Severity Label */}
        <div className={`inline-block px-4 py-1.5 rounded-full text-xs font-semibold uppercase tracking-wider border ${severityStyle.border} ${severityStyle.bg} ${severityStyle.text} mb-4`}>
          {submission.severity}
        </div>

        <p className="text-xs md:text-sm text-[#6b7a68] font-light leading-relaxed max-w-sm mb-6">
          Your responses suggest <strong className="font-semibold text-[#1a2018]">{submission.severity.toLowerCase()}</strong> symptoms. This is a screening tool, not a diagnosis.
        </p>

        {/* Dynamic Sparkline */}
        {sortedHistory.length >= 2 && renderSparkline()}

        {/* List of Recent History */}
        <div className="w-full mt-6 text-left">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-[#9aaa97] mb-2 px-1">
            Recent Check-ins
          </div>
          <div className="max-h-[140px] overflow-y-auto space-y-2 pr-1">
            {[...history]
              .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
              .map((item) => {
                const style = SEVERITY_STYLES[item.severity] || SEVERITY_STYLES["Minimal"];
                return (
                  <div key={item.id} className="flex justify-between items-center bg-white/70 border border-[#e8e0d0]/60 rounded-xl p-3 text-xs shadow-sm">
                    <div className="flex flex-col">
                      <span className={`font-semibold ${style.text}`}>{item.severity}</span>
                      <span className="text-[10px] text-[#9aaa97] mt-0.5">
                        {new Date(item.timestamp).toLocaleDateString(undefined, {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {item.q9_flag && (
                        <span className="material-symbols-outlined text-orange-500 text-base" title="Distress Flag">
                          warning
                        </span>
                      )}
                      <span className="font-mono text-sm font-semibold bg-[#faf9f6] border border-[#e8e0d0] px-2 py-1 rounded-lg">
                        {item.score}
                      </span>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        {/* Verbatim API Disclaimer */}
        <div className="w-full border-t border-[#e8e0d0] mt-6 pt-4 text-[10px] text-[#9aaa97] font-light leading-relaxed text-center">
          {submission.disclaimer}
        </div>

        {/* Return Button */}
        <button
          type="button"
          onClick={() => navigate('/chat')}
          className="w-full bg-[#4a7c59] hover:bg-[#2d5a54] text-white py-3.5 rounded-full text-xs font-semibold uppercase tracking-wider mt-6 transition-all duration-200 active:scale-95 shadow-sm hover:shadow"
        >
          Back to chat
        </button>
      </div>
    </div>
  );
};

export default Phq9Result;
