import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';

// Lazy load pages
const AuthPage3D = lazy(() => import('./pages/AuthPage3D'));
const PendingApprovalPage = lazy(() => import('./pages/PendingApprovalPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const PlaylistPage = lazy(() => import('./pages/Playlist'));
const PendingUsers = lazy(() => import('./pages/admin/PendingUsers'));
const AuthCallback = lazy(() => import('./pages/AuthCallback'));
const ChannelManager = lazy(() => import('./pages/ChannelManager'));
const SchedulePage = lazy(() => import('./pages/SchedulePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const Monitoring = lazy(() => import('./pages/Monitoring'));

const LoadingFallback = () => (
  <div className="flex h-screen w-full items-center justify-center bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
    Loading...
  </div>
);

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/auth" element={<AuthPage3D />} />
            <Route path="/login" element={<AuthPage3D />} />
            <Route path="/pending-approval" element={<PendingApprovalPage />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/admin" element={<Navigate to="/dashboard" replace />} />
              <Route path="/admin/pending" element={<PendingUsers />} />
              <Route path="/admin/monitoring" element={<Monitoring />} />
              <Route path="/channels" element={<ChannelManager />} />
              <Route path="/playlist" element={<PlaylistPage />} />
              <Route path="/schedule" element={<SchedulePage />} />
            </Route>
          </Routes>
        </Suspense>
      </Router>
    </AuthProvider>
  );
};

export default App;

