import React from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import logoUrl from '../assets/raahat_light-removebg-preview.png';

const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-[#fdfcf9] flex flex-col justify-center items-center p-6 relative overflow-hidden select-none">
      {/* Ambient background blurs */}
      <div className="absolute top-[-10%] left-[-10%] w-[35vw] h-[35vw] rounded-full bg-[#e8f0eb] opacity-65 blur-[90px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[35vw] h-[35vw] rounded-full bg-[#f5e8d5] opacity-55 blur-[90px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="max-w-md text-center z-10 flex flex-col items-center"
      >
        <div className="w-16 h-16 rounded-2xl bg-[#E3DFF2]/20 flex items-center justify-center mb-6">
          <img src={logoUrl} alt="Raahat" className="w-11 h-11 object-contain" />
        </div>

        <h1 className="font-serif text-6xl text-[#4a7c59] font-normal tracking-tight mb-2">404</h1>
        <h2 className="font-serif text-2xl text-[#1a2018] font-normal mb-3">This path feels quiet</h2>
        
        <p className="text-sm text-[#6b7a68] font-light leading-relaxed max-w-xs mb-8">
          The page you are looking for doesn't exist, or has moved to a quieter corner. Let's head back to where it is familiar.
        </p>

        <Link
          to="/"
          className="bg-[#4a7c59] hover:bg-[#2d5a54] text-white px-8 py-3 rounded-full text-xs font-semibold uppercase tracking-wider shadow-sm hover:shadow-md transition-all active:scale-95 duration-200"
        >
          Return Home
        </Link>
      </motion.div>
    </div>
  );
};

export default NotFoundPage;
