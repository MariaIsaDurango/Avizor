import { Platform } from 'react-native';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import { apiFetch } from './api';

export async function registerDevice(): Promise<void> {
  const { status } = await Notifications.requestPermissionsAsync();
  if (status !== 'granted') return;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'Alertas Avizor',
      importance: Notifications.AndroidImportance.HIGH,
      sound: 'default',
    });
  }

  const projectId = Constants.expoConfig?.extra?.eas?.projectId as string | undefined;
  const { data: pushToken } = await Notifications.getExpoPushTokenAsync(
    projectId ? { projectId } : {},
  );

  await apiFetch('/api/v1/devices', {
    method: 'POST',
    body: JSON.stringify({
      platform: Platform.OS as 'ios' | 'android',
      app_version: Constants.expoConfig?.version ?? '1.0.0',
      push_token: pushToken,
    }),
  });
}
