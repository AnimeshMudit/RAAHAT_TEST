import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LandingPage from '../pages/LandingPage';
import LoginPage from '../pages/LoginPage';
import OnboardingPage from '../pages/OnboardingPage';
import ChatPage from '../pages/ChatPage';
import NotFoundPage from '../pages/NotFoundPage';

// Route Guard for authenticated pages (/chat, /onboarding)
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#fdfcf9] flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-2 border-[#4a7c59]/30 border-t-[#4a7c59] rounded-full animate-spin" />
        <span className="text-xs text-[#9aaa97] font-light font-sans">Connecting to RAAHAT...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Route Guard for guests only (/login)
const GuestRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#fdfcf9] flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 border-2 border-[#4a7c59]/30 border-t-[#4a7c59] rounded-full animate-spin" />
        <span className="text-xs text-[#9aaa97] font-light font-sans">Connecting to RAAHAT...</span>
      </div>
    );
  }

  if (user) {
    if (!user.name || !user.name.trim()) {
      return <Navigate to="/onboarding" replace />;
    }
    return <Navigate to="/chat" replace />;
  }

  return <>{children}</>;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Pages */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/landing" element={<LandingPage />} />

      {/* Guest Pages */}
      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />

      {/* Protected Pages */}
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <OnboardingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />

      {/* 404 Fallback */}
      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
};
export default AppRoutes;
