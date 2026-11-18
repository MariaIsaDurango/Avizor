import { useEffect, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import * as Notifications from 'expo-notifications';
import RootNavigator from './src/navigation/RootNavigator';
import { navigationRef } from './src/navigation/navigationRef';
import { STORAGE_KEYS } from './src/constants/storage';
import { getAlert } from './src/services/alerts';
import { registerDevice } from './src/services/devices';
import { AccessibilityProvider } from './src/contexts/AccessibilityContext';

type SavedMode = 'senior' | 'tutor' | null;

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

async function handleNotificationResponse(
  response: Notifications.NotificationResponse,
): Promise<void> {
  const data = response.notification.request.content.data as { alert_id?: string };
  if (!data.alert_id) return;
  try {
    const alert = await getAlert(data.alert_id);
    if (navigationRef.isReady()) {
      navigationRef.navigate('AlertDetail', { alert });
    }
  } catch {
    // alerta no encontrada o sesión expirada — el interceptor 401 redirige si hace falta
  }
}

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
        if (mode === 'tutor') {
          registerDevice().catch((e) => {
            if (__DEV__) console.warn('[App] registerDevice failed:', e);
          });
        }
      })
      .catch(() => {
        setInitialMode(null);
        setHasDeviceId(false);
      });

    const subscription = Notifications.addNotificationResponseReceivedListener(
      handleNotificationResponse,
    );
    return () => subscription.remove();
  }, []);

  if (initialMode === undefined || hasDeviceId === undefined) return null;

  return (
    <AccessibilityProvider>
      <NavigationContainer
        ref={navigationRef}
        onReady={() => {
          // ES: Notificación pendiente si la app estaba cerrada al llegar el push.
          // EN: Pending notification if the app was closed when the push arrived.
          Notifications.getLastNotificationResponseAsync().then((response) => {
            if (response) handleNotificationResponse(response);
          });
        }}
      >
        <StatusBar style="auto" />
        <RootNavigator initialMode={initialMode} hasDeviceId={hasDeviceId} />
      </NavigationContainer>
    </AccessibilityProvider>
  );
}
