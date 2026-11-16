import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import { AndroidImportance } from 'expo-notifications';
import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';
import { apiFetch } from './api';
import { STORAGE_KEYS } from '../constants/storage';

export async function registerDevice(): Promise<void> {
  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') return;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Alertas Avizor',
      importance: AndroidImportance.HIGH,
      sound: 'default',
    });
  }

  const projectId = Constants.expoConfig?.extra?.eas?.projectId as string | undefined;
  const { data: pushToken } = await Notifications.getExpoPushTokenAsync(
    projectId ? { projectId } : {},
  );

  const response = await apiFetch('/api/v1/devices', {
    method: 'POST',
    body: JSON.stringify({
      platform: Platform.OS as 'ios' | 'android',
      app_version: Constants.expoConfig?.version ?? '1.0.0',
      push_token: pushToken,
    }),
  });

  if (response.ok) {
    const device: { id: string } = await response.json();
    await SecureStore.setItemAsync(STORAGE_KEYS.DEVICE_ID, device.id);
  } else if (__DEV__) {
    console.warn('[devices] POST /devices failed:', response.status);
  }
}

export async function unregisterDevice(): Promise<void> {
  const deviceId = await SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID);
  if (!deviceId) return;
  try {
    await apiFetch(`/api/v1/devices/${deviceId}`, { method: 'DELETE' });
  } catch {
    if (__DEV__) console.warn('[devices] DELETE /devices failed');
  }
  await SecureStore.deleteItemAsync(STORAGE_KEYS.DEVICE_ID);
}
