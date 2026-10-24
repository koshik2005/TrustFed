import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import DashboardLayout from '@/layouts/DashboardLayout';

// Pages (will be created as you provide HTML designs)
import LoginPage from '@/pages/auth/LoginPage';

// Lazy-loaded pages — add as you build each one
import { lazy, Suspense } from 'react';
const HospitalDashboard  = lazy(() => import('@/pages/dashboard/HospitalDashboard'));
const GlobalMonitor      = lazy(() => import('@/pages/training/GlobalMonitor'));
const PredictionPage     = lazy(() => import('@/pages/prediction/PredictionPage'));
const ExplainPage        = lazy(() => import('@/pages/explainability/ExplainPage'));
const FairnessPage       = lazy(() => import('@/pages/fairness/FairnessPage'));
const PrivacyPage        = lazy(() => import('@/pages/privacy/PrivacyPage'));
const RegionalPage       = lazy(() => import('@/pages/regional/RegionalPage'));
const ComparisonPage     = lazy(() => import('@/pages/comparison/ComparisonPage'));
const AuditPage          = lazy(() => import('@/pages/audit/AuditPage'));
const SettingsPage       = lazy(() => import('@/pages/settings/SettingsPage'));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-full min-h-screen">
      <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function App() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected — all inside DashboardLayout */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"   element={<HospitalDashboard />} />
          <Route path="training"    element={<GlobalMonitor />} />
          <Route path="prediction"  element={<PredictionPage />} />
          <Route path="explain"     element={<ExplainPage />} />
          <Route path="fairness"    element={<FairnessPage />} />
          <Route path="privacy"     element={<PrivacyPage />} />
          <Route path="regional"    element={<RegionalPage />} />
          <Route path="comparison"  element={<ComparisonPage />} />
          <Route path="audit"       element={<AuditPage />} />
          <Route path="settings"    element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
