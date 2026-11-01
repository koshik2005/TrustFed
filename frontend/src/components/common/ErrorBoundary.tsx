import React, { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled TrustFed UI exception:', error, errorInfo);
    // Automatic silent recovery for stale build chunk hashes after a new production deployment
    if (
      error.message?.includes('Failed to fetch dynamically imported module') ||
      error.message?.includes('Importing a module script failed') ||
      error.message?.includes('error loading dynamically imported module')
    ) {
      const hasReloaded = sessionStorage.getItem('stale_chunk_auto_reloaded');
      if (!hasReloaded) {
        sessionStorage.setItem('stale_chunk_auto_reloaded', 'true');
        window.location.reload();
      }
    }
  }

  private handleReload = () => {
    sessionStorage.removeItem('stale_chunk_auto_reloaded');
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  public render() {
    if (this.state.hasError) {
      const isChunkMismatch =
        this.state.error?.message?.includes('Failed to fetch dynamically imported module') ||
        this.state.error?.message?.includes('Importing a module script failed') ||
        this.state.error?.message?.includes('error loading dynamically imported module');

      return (
        <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 p-6">
          <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200 p-8 shadow-xl text-center flex flex-col items-center">
            <div className={`w-16 h-16 rounded-2xl ${isChunkMismatch ? 'bg-blue-50 border-blue-200 text-blue-600' : 'bg-red-50 border-red-200 text-red-600'} border flex items-center justify-center mb-5 shadow-xs`}>
              {isChunkMismatch ? <RefreshCw className="w-8 h-8" /> : <AlertTriangle className="w-8 h-8" />}
            </div>

            <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${isChunkMismatch ? 'bg-blue-100 text-blue-800 border-blue-200' : 'bg-red-100 text-red-800 border-red-200'} border mb-3`}>
              {isChunkMismatch ? 'New Version Deployed' : 'Application Error'}
            </span>

            <h1 className="text-xl font-bold text-slate-900 mb-2">
              {isChunkMismatch ? 'Update Available' : 'Something went wrong'}
            </h1>

            <p className="text-sm text-slate-600 mb-6 leading-relaxed">
              {isChunkMismatch
                ? 'TrustFed was just updated with recent improvements. Please reload the page to synchronize your browser with the latest deployment.'
                : 'An unexpected error occurred while rendering the clinical interface. Patient data remains securely encrypted and isolated.'}
            </p>

            {this.state.error && !isChunkMismatch && (
              <div className="w-full bg-slate-950 text-emerald-400 font-mono text-[11px] p-3 rounded-xl mb-6 text-left overflow-x-auto max-h-32 border border-slate-800">
                {this.state.error.message}
              </div>
            )}

            <div className="flex items-center gap-3 w-full">
              <Button
                variant="outline"
                onClick={this.handleReload}
                className="flex-1 rounded-xl text-xs font-medium border-slate-200 hover:bg-slate-100"
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                {isChunkMismatch ? 'Update & Reload' : 'Reload Page'}
              </Button>
              <Button
                onClick={this.handleGoHome}
                className="flex-1 rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
              >
                <Home className="w-3.5 h-3.5 mr-1.5" />
                Dashboard
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
