import { FileQuestion, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

export default function NotFound404() {
  const navigate = useNavigate();

  return (
    <div className="min-h-[75vh] flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl border border-slate-200/90 p-8 shadow-xl text-center flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-500 mb-5 shadow-xs">
          <FileQuestion className="w-8 h-8" />
        </div>

        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 mb-3">
          HTTP 404 • Not Found
        </span>

        <h1 className="text-xl font-bold text-slate-900 mb-2">
          Page Not Found
        </h1>

        <p className="text-sm text-slate-600 mb-6 leading-relaxed">
          The requested clinical endpoint or view does not exist or has been relocated within the federation network.
        </p>

        <Button
          onClick={() => navigate('/dashboard')}
          className="w-full rounded-xl text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
        >
          <Home className="w-3.5 h-3.5 mr-1.5" />
          Return to Dashboard
        </Button>
      </div>
    </div>
  );
}
