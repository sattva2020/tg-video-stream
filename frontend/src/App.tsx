import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AuthProvider } from './context/AuthContext';
import { LogCollectorProvider } from './context/LogCollectorContext';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import { UserRole } from './types/user';
import { I18nDebugPanel } from './components/debug/I18nDebugPanel';
import ReportBugButton from './components/ReportBugButton';

// Lazy load pages
const AuthPage3D = lazy(() => import('./pages/AuthPage3D'));
const PendingApprovalPage = lazy(() => import('./pages/PendingApprovalPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const PlaylistPage = lazy(() => import('./pages/Playlist'));
const UsersPage = lazy(() => import('./pages/UsersPage'));
const AuthCallback = lazy(() => import('./pages/AuthCallback'));
const ChannelManager = lazy(() => import('./pages/ChannelManager'));
const SchedulePage = lazy(() => import('./pages/SchedulePage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const Monitoring = lazy(() => import('./pages/Monitoring'));
const Analytics = lazy(() => import('./pages/admin/Analytics'));
const NotificationsPage = lazy(() => import('./pages/notifications/Channels'));
const NotificationRulesPage = lazy(() => import('./pages/notifications/Rules'));
const NotificationLogsPage = lazy(() => import('./pages/notifications/Logs'));
const NotificationTemplatesPage = lazy(() => import('./pages/notifications/Templates'));
const NotificationRecipientsPage = lazy(() => import('./pages/notifications/Recipients'));
const StreamQualityPage = lazy(() => import('./pages/admin/StreamQualityPage'));
const UserPlaylistsPage = lazy(() => import('./pages/admin/PlaylistsPage').then(module => ({ default: module.PlaylistsPage })));
const UserPlaylistEditor = lazy(() => import('./components/playlists/PlaylistEditor').then(module => ({ default: module.PlaylistEditor })));
const IncidentsPage = lazy(() => import('./pages/admin/IncidentsPage'));
const AdminSettingsPage = lazy(() => import('./pages/admin/SettingsPage'));
const SessionsPage = lazy(() => import('./pages/admin/SessionsPage'));

// Role groups for RBAC
const OPERATOR_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR, UserRole.OPERATOR];
const ADMIN_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN];
const MODERATOR_AND_ABOVE = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MODERATOR];

const LoadingFallback = () => {
  const { t } = useTranslation();
  
  return (
    <div className="flex h-screen w-full items-center justify-center bg-[color:var(--color-surface)] text-[color:var(--color-text)]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-cyan-500 border-t-transparent"></div>
        <span className="text-sm text-[color:var(--color-text-muted)]">{t('common.loading', 'Загрузка...')}</span>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  // Проверка DEBUG режима для отображения панели отладки i18n
  const showI18nDebug = import.meta.env.DEV || localStorage.getItem('i18n_debug') === 'true';
  
  return (
    <Suspense fallback={<LoadingFallback />}>
      <LogCollectorProvider>
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
              <Route path="/user-playlists" element={<UserPlaylistsPage />} />
              <Route path="/user-playlists/:id" element={<UserPlaylistEditor />} />
            </Route>
            
            {/* Routes for OPERATOR and above */}
            <Route element={<ProtectedRoute allowedRoles={OPERATOR_AND_ABOVE} />}>
              <Route path="/channels" element={<ChannelManager />} />
              <Route path="/schedule" element={<SchedulePage />} />
              <Route path="/notifications/channels" element={<NotificationsPage />} />
              <Route path="/notifications/templates" element={<NotificationTemplatesPage />} />
              <Route path="/notifications/recipients" element={<NotificationRecipientsPage />} />
              <Route path="/notifications/rules" element={<NotificationRulesPage />} />
              <Route path="/notifications/logs" element={<NotificationLogsPage />} />
            </Route>
            
            {/* Routes for ADMIN and above */}
            <Route element={<ProtectedRoute allowedRoles={ADMIN_AND_ABOVE} />}>
              <Route path="/admin" element={<Navigate to="/settings" replace />} />
              <Route path="/users" element={<UsersPage />} />
            </Route>
            
            {/* Routes for MODERATOR and above (analytics) */}
            <Route element={<ProtectedRoute allowedRoles={MODERATOR_AND_ABOVE} />}>
              <Route path="/admin/analytics" element={<Analytics />} />
              <Route path="/admin/monitoring" element={<Monitoring />} />
            </Route>

            {/* Routes for ADMIN and above (stream quality) */}
            <Route element={<ProtectedRoute allowedRoles={ADMIN_AND_ABOVE} />}>
              <Route path="/admin/stream-quality" element={<StreamQualityPage />} />
            </Route>

            {/* Routes for MODERATOR and above (incidents) */}
            <Route element={<ProtectedRoute allowedRoles={MODERATOR_AND_ABOVE} />}>
              <Route path="/admin/incidents" element={<IncidentsPage />} />
            </Route>

            {/* Routes for ADMIN only (settings & sessions) */}
            <Route element={<ProtectedRoute allowedRoles={ADMIN_AND_ABOVE} />}>
              <Route path="/admin/settings" element={<AdminSettingsPage />} />
              <Route path="/admin/sessions" element={<SessionsPage />} />
            </Route>
          </Routes>
        </Suspense>
        
        {/* Плавающая кнопка "Сообщить о проблеме" */}
        <ReportBugButton variant="floating" showOnError={true} />
      </Router>
    </AuthProvider>
      </LogCollectorProvider>
      
      {/* Панель отладки i18n (только в режиме разработки) */}
      {showI18nDebug && <I18nDebugPanel />}
    </Suspense>
  );
};

export default App;

