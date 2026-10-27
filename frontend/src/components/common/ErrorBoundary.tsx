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
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 p-6">
          <div className="max-w-md w-full bg-white rounded-2xl border border-red-200 p-8 shadow-xl text-center flex flex-col items-center">
            <div className="w-16 h-16 rounded-2xl bg-red-50 border border-red-200 flex items-center justify-center text-red-600 mb-5 shadow-xs">
              <AlertTriangle className="w-8 h-8" />
            </div>

            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-800 border border-red-200 mb-3">
              Application Error
            </span>

            <h1 className="text-xl font-bold text-slate-900 mb-2">
              Something went wrong
            </h1>

            <p className="text-sm text-slate-600 mb-6 leading-relaxed">
              An unexpected error occurred while rendering the clinical interface.
              Patient data remains securely encrypted and isolated.
            </p>

            {this.state.error && (
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
                Reload Page
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
