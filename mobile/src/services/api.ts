import * as SecureStore from 'expo-secure-store';
import { Alert } from 'react-native';
import { API_BASE_URL } from '../constants/api';
import { navigationRef } from '../navigation/navigationRef';
import { STORAGE_KEYS } from '../constants/storage';

const AUTH_TOKEN_KEY = 'auth_token';

let redirectingOn401 = false;

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync(AUTH_TOKEN_KEY);
}

export async function saveToken(token: string): Promise<void> {
  await SecureStore.setItemAsync(AUTH_TOKEN_KEY, token);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync(AUTH_TOKEN_KEY);
}

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = await getToken();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });

  // no redirigir en endpoints de auth ni en redeem (son públicos)
  if (response.status === 401 && !path.startsWith('/api/v1/auth/') && !path.startsWith('/api/v1/pairings/redeem')) {
    if (redirectingOn401) return response;
    redirectingOn401 = true;
    await clearToken();
    if (navigationRef.isReady()) {
      const mode = await SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE);
      if (mode === 'senior') {
        await SecureStore.deleteItemAsync(STORAGE_KEYS.DEVICE_ID);
        Alert.alert(
          'Sesión cerrada',
          'Tu sesión se ha cerrado. Vuelve a vincularte con tu tutor.',
          [{ text: 'Entendido', onPress: () => {
            redirectingOn401 = false;
            navigationRef.reset({ index: 0, routes: [{ name: 'SeniorPairing' }] });
          }}],
          { cancelable: false },
        );
      } else {
        redirectingOn401 = false;
        navigationRef.reset({ index: 0, routes: [{ name: 'TutorLogin' }] });
      }
    } else {
      redirectingOn401 = false;
    }
  }

  return response;
}
