/// <reference types="vite/client" />

// Extend ImportMeta with Vite-specific env
interface ImportMetaEnv {
  readonly VITE_API_URL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
