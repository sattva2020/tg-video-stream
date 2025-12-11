import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import { UserRole } from './types/user';

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
const Analytics = lazy(() => import('./pages/admin/Analytics'));
const NotificationsPage = lazy(() => import('./pages/notifications/Channels'));
const NotificationRulesPage = lazy(() => import('./pages/notifications/Rules'));
const NotificationLogsPage = lazy(() => import('./pages/notifications/Logs'));

// Role groups for RBAC
const OPERATOR_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR, UserRole.OPERATOR];
const ADMIN_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN];
const MODERATOR_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR];

const LoadingFallback = () => (
  <div className="flex h-screen w-full items-center justify-center bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
    <div className="flex flex-col items-center gap-4">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent"></div>
      <span className="text-sm text-gray-400">Загрузка...</span>
    </div>
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
            
            {/* Routes for all authenticated users */}
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/playlist" element={<PlaylistPage />} />
            </Route>
            
            {/* Routes for OPERATOR and above */}
            <Route element={<ProtectedRoute allowedRoles={OPERATOR_AND_ABOVE} />}>
              <Route path="/channels" element={<ChannelManager />} />
              <Route path="/schedule" element={<SchedulePage />} />
              <Route path="/notifications/channels" element={<NotificationsPage />} />
              <Route path="/notifications/rules" element={<NotificationRulesPage />} />
              <Route path="/notifications/logs" element={<NotificationLogsPage />} />
            </Route>
            
            {/* Routes for ADMIN and above */}
            <Route element={<ProtectedRoute allowedRoles={ADMIN_AND_ABOVE} />}>
              <Route path="/admin" element={<Navigate to="/dashboard" replace />} />
              <Route path="/admin/pending" element={<PendingUsers />} />
              <Route path="/admin/monitoring" element={<Monitoring />} />
            </Route>
            
            {/* Routes for MODERATOR and above (analytics) */}
            <Route element={<ProtectedRoute allowedRoles={MODERATOR_AND_ABOVE} />}>
              <Route path="/admin/analytics" element={<Analytics />} />
            </Route>
          </Routes>
        </Suspense>
      </Router>
    </AuthProvider>
  );
};

export default App;

