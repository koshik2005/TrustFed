import { create } from 'zustand';
import type { TrainingSession, TrainingStatus } from '../types';

interface TrainingStore {
  session: TrainingSession | null;
  status: TrainingStatus;
  setSession: (session: TrainingSession) => void;
  setStatus: (status: TrainingStatus) => void;
  clear: () => void;
}

export const useTrainingStore = create<TrainingStore>((set) => ({
  session: null,
  status: 'idle',
  setSession: (session) => set({ session }),
  setStatus: (status) => set({ status }),
  clear: () => set({ session: null, status: 'idle' }),
}));
