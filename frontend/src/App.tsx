import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import AuthPage3D from './pages/AuthPage3D';
import DashboardPage from './pages/DashboardPage';
import PendingUsers from './pages/admin/PendingUsers';
import AuthCallback from './pages/AuthCallback';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/register" element={<AuthPage3D />} />
          <Route path="/login" element={<AuthPage3D />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/admin/pending" element={<PendingUsers />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;

