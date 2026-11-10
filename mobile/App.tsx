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

  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE)
      .then((value) => setInitialMode((value as SavedMode) ?? null))
      .catch(() => setInitialMode(null));
  }, []);

  if (initialMode === undefined) return null;

  return (
    <NavigationContainer ref={navigationRef}>
      <StatusBar style="auto" />
      <RootNavigator initialMode={initialMode} />
    </NavigationContainer>
  );
}
