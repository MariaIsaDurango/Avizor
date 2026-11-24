import { useEffect, useState } from 'react';
import { DeviceEventEmitter, NativeModules } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import * as SecureStore from 'expo-secure-store';
import * as Notifications from 'expo-notifications';
import * as Haptics from 'expo-haptics';
import RootNavigator from './src/navigation/RootNavigator';
import { navigationRef } from './src/navigation/navigationRef';
import { STORAGE_KEYS } from './src/constants/storage';
import { getAlert } from './src/services/alerts';
import { registerDevice } from './src/services/devices';
import { AccessibilityProvider } from './src/contexts/AccessibilityContext';

const { ShareModule } = NativeModules;

type SavedMode = 'senior' | 'tutor' | null;

Notifications.setNotificationHandler({
  handleNotification: async () => {
    try {
      const raw = await SecureStore.getItemAsync(STORAGE_KEYS.ACCESSIBILITY_PROFILE);
      const profile = raw ? JSON.parse(raw) : null;
      if (profile?.hearing_impairment) {
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
      }
    } catch {}
    return {
      shouldShowAlert: true,
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    };
  },
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

    // ES: Texto compartido cuando la app estaba abierta (DeviceEventEmitter).
    const shareSub = DeviceEventEmitter.addListener('ShareIntentReceived', ({ text }: { text: string }) => {
      if (navigationRef.isReady()) {
        navigationRef.navigate('SeniorShareEmail', { text });
      }
    });

    const subscription = Notifications.addNotificationResponseReceivedListener(
      handleNotificationResponse,
    );
    return () => {
      shareSub.remove();
      subscription.remove();
    };
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
          // ES: Texto compartido en arranque en frío — aquí la navegación ya está lista.
          ShareModule?.getSharedText?.().then((text: string | null) => {
            if (text) navigationRef.navigate('SeniorShareEmail', { text });
          });
        }}
      >
        <StatusBar style="auto" />
        <RootNavigator initialMode={initialMode} hasDeviceId={hasDeviceId} />
      </NavigationContainer>
    </AccessibilityProvider>
  );
}
