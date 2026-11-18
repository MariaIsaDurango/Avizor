import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { STORAGE_KEYS } from '../constants/storage';
import { AccessibilityProfile } from '../services/pairing';

interface AccessibilityContextValue {
  largeText: boolean;
  colorBlind: boolean;
  hardOfHearing: boolean;
  reload: () => void;
}

const AccessibilityContext = createContext<AccessibilityContextValue>({
  largeText: false,
  colorBlind: false,
  hardOfHearing: false,
  reload: () => {},
});

export function AccessibilityProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<AccessibilityProfile | null>(null);

  async function load() {
    try {
      const raw = await SecureStore.getItemAsync(STORAGE_KEYS.ACCESSIBILITY_PROFILE);
      setProfile(raw ? JSON.parse(raw) : null);
    } catch {
      setProfile(null);
    }
  }

  useEffect(() => { load(); }, []);

  const value: AccessibilityContextValue = {
    largeText: !!(profile?.low_vision || profile?.blindness),
    colorBlind: !!profile?.color_blindness,
    hardOfHearing: !!profile?.hearing_impairment,
    reload: load,
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility(): AccessibilityContextValue {
  return useContext(AccessibilityContext);
}
