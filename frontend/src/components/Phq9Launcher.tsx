import React from 'react';

interface Phq9LauncherProps {
  onOpen: () => void;
}

export const Phq9Launcher: React.FC<Phq9LauncherProps> = ({ onOpen }) => {
  return (
    <button
      onClick={onOpen}
      className="w-8 h-8 rounded-full border border-[#e8e0d0] hover:bg-[#f5f0e8]/50 flex items-center justify-center transition-colors text-[#6b7a68] hover:text-[#3d4a3a]"
      title="Mood Check"
      aria-label="Mood Check"
    >
      <span className="material-symbols-outlined text-[20px]">spa</span>
    </button>
  );
};

export default Phq9Launcher;
