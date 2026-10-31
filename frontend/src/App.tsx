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
const RoleDashboardDispatcher = lazy(() => import('@/pages/dashboard/RoleDashboardDispatcher'));
const HospitalDashboard       = lazy(() => import('@/pages/dashboard/HospitalDashboard'));
const RegionalDashboard       = lazy(() => import('@/pages/dashboard/RegionalDashboard'));
const GlobalAdminDashboard    = lazy(() => import('@/pages/dashboard/GlobalAdminDashboard'));
const GlobalMonitor           = lazy(() => import('@/pages/training/GlobalMonitor'));
const PredictionPage          = lazy(() => import('@/pages/prediction/PredictionPage'));
const ExplainPage             = lazy(() => import('@/pages/explainability/ExplainPage'));
const FairnessPage            = lazy(() => import('@/pages/fairness/FairnessPage'));
const PrivacyPage             = lazy(() => import('@/pages/privacy/PrivacyPage'));
const RegionalPage            = lazy(() => import('@/pages/regional/RegionalPage'));
const RegionalHubsPage        = lazy(() => import('@/pages/admin/RegionalHubsPage'));
const ComparisonPage          = lazy(() => import('@/pages/comparison/ComparisonPage'));
const AuditPage               = lazy(() => import('@/pages/audit/AuditPage'));
const SettingsPage            = lazy(() => import('@/pages/settings/SettingsPage'));

// Phase 3: Clinical Patient & Doctor Confirmation Pages
const PatientListPage          = lazy(() => import('@/pages/clinical/PatientListPage'));
const NewPatientEncounterPage = lazy(() => import('@/pages/clinical/NewPatientEncounterPage'));
const PatientDetailPage        = lazy(() => import('@/pages/clinical/PatientDetailPage'));
const EncounterDetailPage      = lazy(() => import('@/pages/clinical/EncounterDetailPage'));
const PendingConfirmationsPage = lazy(() => import('@/pages/clinical/PendingConfirmationsPage'));

import ForcePasswordResetModal from '@/components/auth/ForcePasswordResetModal';

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
            
            {/* Role-Aware Dashboard Router */}
            <Route
              path="dashboard"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'regional_admin', 'global_admin']}>
                  <RoleDashboardDispatcher />
                </RoleRoute>
              }
            />

            {/* Phase 3: Clinical Encounters & Doctor Confirmation Workflow */}
            <Route
              path="patients"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'global_admin']}>
                  <PatientListPage />
                </RoleRoute>
              }
            />
            <Route
              path="patients/new"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'global_admin']}>
                  <NewPatientEncounterPage />
                </RoleRoute>
              }
            />
            <Route
              path="patients/:id"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'global_admin']}>
                  <PatientDetailPage />
                </RoleRoute>
              }
            />
            <Route
              path="encounters/:id"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'global_admin']}>
                  <EncounterDetailPage />
                </RoleRoute>
              }
            />
            <Route
              path="doctor/pending"
              element={
                <RoleRoute allowedRoles={['doctor', 'global_admin']}>
                  <PendingConfirmationsPage />
                </RoleRoute>
              }
            />
            <Route
              path="prediction"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'regional_admin', 'global_admin']}>
                  <PredictionPage />
                </RoleRoute>
              }
            />
            <Route
              path="explain"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'regional_admin', 'global_admin']}>
                  <ExplainPage />
                </RoleRoute>
              }
            />
            <Route
              path="settings"
              element={
                <RoleRoute allowedRoles={['hospital_staff', 'doctor', 'regional_admin', 'global_admin']}>
                  <SettingsPage />
                </RoleRoute>
              }
            />

            {/* Regional & Global Admins */}
            <Route
              path="regional"
              element={
                <RoleRoute allowedRoles={['regional_admin', 'global_admin']}>
                  <RegionalDashboard />
                </RoleRoute>
              }
            />
            <Route
              path="training"
              element={
                <RoleRoute allowedRoles={['global_admin']}>
                  <GlobalAdminDashboard />
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
              path="hubs"
              element={
                <RoleRoute allowedRoles={['global_admin']}>
                  <RegionalHubsPage />
                </RoleRoute>
              }
            />
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
        <ForcePasswordResetModal />
      </Suspense>
    </ErrorBoundary>
  );
}

