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
import { submitAnalysis } from './src/services/analyses';
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

    // ES: Email detectado automáticamente por AccesibilityService en Gmail/Outlook.
    const emailSub = DeviceEventEmitter.addListener(
      'AvizorTextEvent',
      async ({ text, eventType }: { text: string; eventType: string }) => {
        if (eventType !== 'email_body') return;
        try {
          const [mode, deviceId] = await Promise.all([
            SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE),
            SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID),
          ]);
          if (mode !== 'senior' || !deviceId) return;

          const verdict = await submitAnalysis(deviceId, 'text', text, {
            channel: 'screen',
            origin: 'automatic',
          });

          if (verdict.risk_level === 'red' && verdict.block_template) {
            if (navigationRef.isReady()) {
              navigationRef.navigate('SeniorBlock', { template: verdict.block_template });
            }
          } else if (verdict.risk_level === 'amber') {
            await Notifications.scheduleNotificationAsync({
              content: {
                title: 'Revisa este email',
                body: 'Tiene indicios sospechosos. Consulta con un familiar.',
                data: { verdict: verdict.risk_level },
              },
              trigger: null,
            });
          }
        } catch {
          // silent — no interrumpir al sénior si el análisis falla
        }
      },
    );

    // ES: SMS detectado automáticamente por NotificationListenerService.
    const smsSub = DeviceEventEmitter.addListener(
      'AvizorNotificationEvent',
      async ({ text }: { packageName: string; title: string; text: string }) => {
        if (!text.trim()) return;
        try {
          const [mode, deviceId] = await Promise.all([
            SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE),
            SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID),
          ]);
          if (mode !== 'senior' || !deviceId) return;

          const verdict = await submitAnalysis(deviceId, 'text', text, {
            channel: 'sms',
            origin: 'automatic',
          });

          if (verdict.risk_level === 'red' && verdict.block_template) {
            if (navigationRef.isReady()) {
              navigationRef.navigate('SeniorBlock', { template: verdict.block_template });
            }
          } else if (verdict.risk_level === 'amber') {
            await Notifications.scheduleNotificationAsync({
              content: {
                title: 'SMS sospechoso',
                body: 'Has recibido un SMS con indicios sospechosos. Consulta con un familiar.',
                data: { verdict: verdict.risk_level },
              },
              trigger: null,
            });
          }
        } catch {
          // silent — no interrumpir al sénior si el análisis falla
        }
      },
    );

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
      emailSub.remove();
      smsSub.remove();
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
