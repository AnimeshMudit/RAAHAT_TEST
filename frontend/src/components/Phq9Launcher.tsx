import React from 'react';

interface Phq9LauncherProps {
  onOpen: () => void;
}

export const Phq9Launcher: React.FC<Phq9LauncherProps> = ({ onOpen }) => {
  return (
    <button
      onClick={onOpen}
      type="button"
      title="Mood Check"
      aria-label="Mood Check"
      className="inline-flex items-center gap-1.5 h-8 px-3 rounded-full border border-[#e8e0d0] bg-white/70 hover:bg-[#f5f0e8]/70 transition-colors text-[#3d4a3a] hover:text-[#2d5a54] text-xs font-medium"
    >
      <span className="material-symbols-outlined text-[18px] leading-none">spa</span>
      <span className="leading-none">Mood Check</span>
    </button>
  );
};

export default Phq9Launcher;
