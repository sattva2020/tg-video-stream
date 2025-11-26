import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';

// Lazy load pages
const AuthPage3D = lazy(() => import('./pages/AuthPage3D'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const PendingUsers = lazy(() => import('./pages/admin/PendingUsers'));
const AuthCallback = lazy(() => import('./pages/AuthCallback'));

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
            <Route path="/register" element={<AuthPage3D />} />
            <Route path="/login" element={<AuthPage3D />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/admin/pending" element={<PendingUsers />} />
            </Route>
          </Routes>
        </Suspense>
      </Router>
    </AuthProvider>
  );
};

export default App;

