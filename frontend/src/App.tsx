import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect, lazy, Suspense } from 'react';
import { useAuthStore } from '@/store/authStore';
import DashboardLayout from '@/layouts/DashboardLayout';
import RoleRoute from '@/components/common/RoleRoute';
import ErrorBoundary from '@/components/common/ErrorBoundary';

// Public & Error Pages
import LoginPage from '@/pages/auth/LoginPage';
import Forbidden403 from '@/pages/error/Forbidden403';
import NotFound404 from '@/pages/error/NotFound404';

// Lazy-loaded pages
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
  useEffect(() => {
    // Attempt silent session restore on startup via httpOnly refresh token cookie
    useAuthStore.getState().initializeAuth();
  }, []);

  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingFallback />}>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/403" element={<Forbidden403 />} />
          <Route path="/404" element={<NotFound404 />} />

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
            
            {/* Hospital & Above */}
            <Route
              path="dashboard"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'regional_admin', 'global_admin']}>
                  <HospitalDashboard />
                </RoleRoute>
              }
            />
            <Route
              path="prediction"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'regional_admin', 'global_admin']}>
                  <PredictionPage />
                </RoleRoute>
              }
            />
            <Route
              path="explain"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'regional_admin', 'global_admin']}>
                  <ExplainPage />
                </RoleRoute>
              }
            />
            <Route
              path="settings"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'regional_admin', 'global_admin']}>
                  <SettingsPage />
                </RoleRoute>
              }
            />

            {/* Regional & Global Admins */}
            <Route
              path="regional"
              element={
                <RoleRoute allowedRoles={['regional_admin', 'global_admin']}>
                  <RegionalPage />
                </RoleRoute>
              }
            />
            <Route
              path="training"
              element={
                <RoleRoute allowedRoles={['regional_admin', 'global_admin']}>
                  <GlobalMonitor />
                </RoleRoute>
              }
            />
            <Route
              path="comparison"
              element={
                <RoleRoute allowedRoles={['regional_admin', 'global_admin']}>
                  <ComparisonPage />
                </RoleRoute>
              }
            />

            {/* Global Admins Only */}
            <Route
              path="fairness"
              element={
                <RoleRoute allowedRoles={['global_admin']}>
                  <FairnessPage />
                </RoleRoute>
              }
            />
            <Route
              path="privacy"
              element={
                <RoleRoute allowedRoles={['global_admin']}>
                  <PrivacyPage />
                </RoleRoute>
              }
            />
            <Route
              path="audit"
              element={
                <RoleRoute allowedRoles={['global_admin']}>
                  <AuditPage />
                </RoleRoute>
              }
            />
          </Route>

          {/* Catch-all */}
          <Route path="*" element={<NotFound404 />} />
        </Routes>
      </Suspense>
    </ErrorBoundary>
  );
}

