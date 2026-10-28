export const getBaseUrl = (): string => {
  let envUrl = import.meta.env.VITE_API_URL;
  if (envUrl && envUrl.trim()) {
    envUrl = envUrl.trim().replace(/\/+$/, '');
    return envUrl.endsWith('/api') ? envUrl : `${envUrl}/api`;
  }
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return '/api';
  }
  return 'http://localhost:8000/api';
};
