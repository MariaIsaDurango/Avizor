import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import * as SecureStore from 'expo-secure-store';
import { STORAGE_KEYS } from '../constants/storage';
import { AccessibilityProfile, getSeniorProfile } from '../services/pairing';

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

  function load() {
    SecureStore.getItemAsync(STORAGE_KEYS.ACCESSIBILITY_PROFILE)
      .then((raw) => setProfile(raw ? (JSON.parse(raw) as AccessibilityProfile) : null))
      .catch(() => setProfile(null));

    SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE)
      .then((mode) => {
        if (mode !== 'senior') return;
        return getSeniorProfile().then((seniorProfile) => {
          const serverProfile = seniorProfile.accessibility_profile;
          if (serverProfile) {
            SecureStore.setItemAsync(STORAGE_KEYS.ACCESSIBILITY_PROFILE, JSON.stringify(serverProfile)).catch(() => {});
            setProfile(serverProfile);
          } else {
            SecureStore.deleteItemAsync(STORAGE_KEYS.ACCESSIBILITY_PROFILE).catch(() => {});
            setProfile(null);
          }
          if (seniorProfile.guardian_phone) {
            SecureStore.setItemAsync(STORAGE_KEYS.GUARDIAN_PHONE, seniorProfile.guardian_phone).catch(() => {});
          } else {
            SecureStore.deleteItemAsync(STORAGE_KEYS.GUARDIAN_PHONE).catch(() => {});
          }
        });
      })
      .catch(() => {});
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
