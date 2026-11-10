import { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import RootNavigator from './src/navigation/RootNavigator';
import { navigationRef } from './src/navigation/navigationRef';
import { STORAGE_KEYS } from './src/constants/storage';

type SavedMode = 'senior' | 'tutor' | null;

export default function App() {
  const [initialMode, setInitialMode] = useState<SavedMode | undefined>(undefined);
  const [hasDeviceId, setHasDeviceId] = useState<boolean | undefined>(undefined);

  useEffect(() => {
    Promise.all([
      SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE),
      SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID),
    ])
      .then(([mode, deviceId]) => {
        setInitialMode((mode as SavedMode) ?? null);
        setHasDeviceId(deviceId !== null);
      })
      .catch(() => {
        setInitialMode(null);
        setHasDeviceId(false);
      });
  }, []);

  if (initialMode === undefined || hasDeviceId === undefined) return null;

  return (
    <NavigationContainer ref={navigationRef}>
      <StatusBar style="auto" />
      <RootNavigator initialMode={initialMode} hasDeviceId={hasDeviceId} />
    </NavigationContainer>
  );
}
