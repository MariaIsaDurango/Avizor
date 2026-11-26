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

const TEMPLATE_NOTIFICATION_BODY: Record<string, string> = {
  FAKE_DO_NOT_TOUCH: 'No toques nada en este mensaje.',
  DANGEROUS_LINK:    'No hagas clic en ningún enlace.',
  SUSPICIOUS_CALL:   'No llames al número indicado sin consultar.',
  ASKS_BANK_DETAILS: 'Nunca compartas tus datos bancarios ni contraseñas.',
  UNSURE_CALL_FAMILY:'Consulta con un familiar antes de responder.',
};

const TEMPLATE_NOTIFICATION_BODY_SOLO: Record<string, string> = {
  FAKE_DO_NOT_TOUCH: 'No toques nada en este mensaje.',
  DANGEROUS_LINK:    'No hagas clic en ningún enlace.',
  SUSPICIOUS_CALL:   'No llames a ese número. Verifica llamando al número oficial de la entidad.',
  ASKS_BANK_DETAILS: 'Nunca compartas tus datos bancarios ni contraseñas.',
  UNSURE_CALL_FAMILY:'No respondas. Verifica contactando con la entidad a través de sus canales oficiales.',
};

type SavedMode = 'senior' | 'tutor' | 'senior_solo' | null;

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
  const [hasConsent, setHasConsent]   = useState<boolean | undefined>(undefined);

  useEffect(() => {
    Promise.all([
      SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE),
      SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID),
      SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_GIVEN),
      SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_SKIPPED),
    ])
      .then(([mode, deviceId, consentGiven, consentSkipped]) => {
        setInitialMode((mode as SavedMode) ?? null);
        setHasDeviceId(deviceId !== null);
        const withinSkipWindow = consentSkipped
          ? Date.now() - Number(consentSkipped) < 7 * 24 * 60 * 60 * 1000
          : false;
        setHasConsent(consentGiven === 'true' || withinSkipWindow);
        if (mode === 'tutor') {
          registerDevice().catch((e) => {
            if (__DEV__) console.warn('[App] registerDevice failed:', e);
          });
        }
      })
      .catch(() => {
        setInitialMode(null);
        setHasDeviceId(false);
        setHasConsent(false);
      });

    // ES: Email detectado automáticamente por AccesibilityService en Gmail/Outlook.
    const emailSub = DeviceEventEmitter.addListener(
      'AvizorTextEvent',
      async ({ text, eventType }: { text: string; eventType: string }) => {
        if (eventType !== 'email_body') return;
        try {
          const [mode, deviceId, consentGiven] = await Promise.all([
            SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE),
            SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID),
            SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_GIVEN),
          ]);
          if ((mode !== 'senior' && mode !== 'senior_solo') || !deviceId) return;
          if (mode === 'senior_solo' && consentGiven !== 'true') return;

          const verdict = await submitAnalysis(deviceId, 'text', text, {
            channel: 'screen',
            origin: 'automatic',
          });

          if (verdict.risk_level === 'red' && verdict.block_template) {
            if (navigationRef.isReady()) {
              navigationRef.navigate('SeniorBlock', { template: verdict.block_template });
            }
          } else if (verdict.risk_level === 'amber') {
            const bodyMap = mode === 'senior_solo' ? TEMPLATE_NOTIFICATION_BODY_SOLO : TEMPLATE_NOTIFICATION_BODY;
            const fallback = mode === 'senior_solo' ? 'Verifica contactando con la entidad a través de sus canales oficiales.' : 'Consulta con un familiar antes de responder.';
            const advice = (verdict.block_template && bodyMap[verdict.block_template]) ?? fallback;
            await Notifications.scheduleNotificationAsync({
              content: {
                title: 'Revisa este email',
                body: advice,
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
          const [mode, deviceId, consentGiven] = await Promise.all([
            SecureStore.getItemAsync(STORAGE_KEYS.USER_MODE),
            SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID),
            SecureStore.getItemAsync(STORAGE_KEYS.CONSENT_GIVEN),
          ]);
          if ((mode !== 'senior' && mode !== 'senior_solo') || !deviceId) return;
          if (mode === 'senior_solo' && consentGiven !== 'true') return;

          const verdict = await submitAnalysis(deviceId, 'text', text, {
            channel: 'sms',
            origin: 'automatic',
          });

          if (verdict.risk_level === 'red' && verdict.block_template) {
            if (navigationRef.isReady()) {
              navigationRef.navigate('SeniorBlock', { template: verdict.block_template });
            }
          } else if (verdict.risk_level === 'amber') {
            const bodyMap = mode === 'senior_solo' ? TEMPLATE_NOTIFICATION_BODY_SOLO : TEMPLATE_NOTIFICATION_BODY;
            const fallback = mode === 'senior_solo' ? 'Verifica contactando con la entidad a través de sus canales oficiales.' : 'Consulta con un familiar antes de responder.';
            const advice = (verdict.block_template && bodyMap[verdict.block_template]) ?? fallback;
            await Notifications.scheduleNotificationAsync({
              content: {
                title: 'SMS sospechoso',
                body: advice,
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

    // ES: Contenido compartido cuando la app estaba abierta (DeviceEventEmitter).
    const shareSub = DeviceEventEmitter.addListener(
      'ShareIntentReceived',
      (payload: { text?: string; uri?: string; mimeType?: string }) => {
        if (!navigationRef.isReady()) return;
        if (payload.uri) {
          navigationRef.navigate('SeniorShareEmail', { fileUri: payload.uri, mimeType: payload.mimeType });
        } else if (payload.text) {
          navigationRef.navigate('SeniorShareEmail', { text: payload.text });
        }
      },
    );

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

  if (initialMode === undefined || hasDeviceId === undefined || hasConsent === undefined) return null;

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
          // ES: Contenido compartido en arranque en frío — aquí la navegación ya está lista.
          ShareModule?.getSharedText?.().then((text: string | null) => {
            if (text) navigationRef.navigate('SeniorShareEmail', { text });
          });
          ShareModule?.getSharedFile?.().then((file: { uri: string; mimeType: string } | null) => {
            if (file) navigationRef.navigate('SeniorShareEmail', { fileUri: file.uri, mimeType: file.mimeType });
          });
        }}
      >
        <StatusBar style="auto" />
        <RootNavigator initialMode={initialMode} hasDeviceId={hasDeviceId} hasConsent={hasConsent} />
      </NavigationContainer>
    </AccessibilityProvider>
  );
}
