-- ==============================================================================
-- TrustFed AI | Row Level Security (RLS) Remediation Script
-- Remediation for Supabase Security Advisor finding:
-- "RLS is disabled on 16 public tables"
-- ==============================================================================

-- 1. Enable Row Level Security (RLS) on all 16 public application tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regional_hubs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hospitals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.encounters ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.diseases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.model_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.consent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.patient_predictions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fl_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.round_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hospital_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fairness_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.privacy_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.refresh_tokens ENABLE ROW LEVEL SECURITY;

-- 2. Revoke all permissions from PostgREST client roles (anon and authenticated)
-- Ensures no direct client API reads or writes can bypass the FastAPI backend.
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM anon, authenticated;
REVOKE ALL ON ALL ROUTINES IN SCHEMA public FROM anon, authenticated;

-- 3. Create service_role full-access policies
-- Allows Supabase internal backend tools, dashboard, and service-role requests to query tables if needed.
DO $$
DECLARE
    tbl text;
    tables text[] := ARRAY[
        'users', 'regional_hubs', 'hospitals', 'patients', 'encounters',
        'diseases', 'model_versions', 'consent_records', 'audit_logs',
        'patient_predictions', 'fl_sessions', 'round_metrics', 'hospital_nodes',
        'fairness_reports', 'privacy_reports', 'refresh_tokens'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_policies 
            WHERE schemaname = 'public' 
              AND tablename = tbl 
              AND policyname = 'service_role_full_access'
        ) THEN
            EXECUTE format('CREATE POLICY "service_role_full_access" ON public.%I FOR ALL TO service_role USING (true) WITH CHECK (true);', tbl);
        END IF;
    END LOOP;
END $$;

