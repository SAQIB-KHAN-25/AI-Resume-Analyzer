import React, { useEffect, useState } from 'react';
import { Toaster } from 'react-hot-toast';

import AuthPage from './components/auth/AuthPage';
import AppShell from './components/layout/AppShell';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Analyze from './pages/Analyze';
import BulkAnalyze from './pages/BulkAnalyze';
import History from './pages/History';

export default function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    try {
      const token = localStorage.getItem('authToken');
      const userStr = localStorage.getItem('user');
      if (token && userStr) setUser(JSON.parse(userStr));
    } catch {
      localStorage.removeItem('authToken');
      localStorage.removeItem('user');
    } finally {
      setAuthChecked(true);
    }
  }, []);

  const onAuthSuccess = () => {
    const userStr = localStorage.getItem('user');
    if (userStr) setUser(JSON.parse(userStr));
  };

  const onLogout = () => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    setUser(null);
    setActiveTab('home');
  };

  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center text-slate-400">Loading…</div>
    );
  }

  return (
    <>
      <Toaster
        position="top-right"
        gutter={10}
        toastOptions={{
          duration: 4000,
          style: {
            background: 'rgba(15, 23, 42, 0.95)',
            color: '#f8fafc',
            fontSize: '13.5px',
            fontWeight: 500,
            borderRadius: '12px',
            padding: '10px 14px',
            boxShadow: '0 10px 30px -12px rgba(15, 23, 42, 0.5)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(148, 163, 184, 0.15)',
            maxWidth: '380px',
          },
          success: {
            iconTheme: { primary: '#10b981', secondary: '#f8fafc' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#f8fafc' },
            duration: 5000,
          },
        }}
      />
      {!user ? (
        <AuthPage onAuthSuccess={onAuthSuccess} />
      ) : (
        <AppShell
          user={user}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onLogout={onLogout}
          onUserUpdate={(updated) => {
            setUser(updated);
            localStorage.setItem('user', JSON.stringify(updated));
          }}
        >
          {activeTab === 'home' && <Home user={user} onNavigate={setActiveTab} />}
          {activeTab === 'dashboard' && <Dashboard user={user} onNavigate={setActiveTab} />}
          {activeTab === 'analyze' && <Analyze />}
          {activeTab === 'bulk' && <BulkAnalyze />}
          {activeTab === 'history' && <History onNavigate={setActiveTab} />}
        </AppShell>
      )}
    </>
  );
}
