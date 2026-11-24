import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { RootStackParamList } from './types';
import WelcomeScreen from '../screens/onboarding/WelcomeScreen';
import ModeSelectionScreen from '../screens/onboarding/ModeSelectionScreen';
import SeniorConsentScreen from '../screens/onboarding/SeniorConsentScreen';
import TutorLoginScreen from '../screens/auth/TutorLoginScreen';
import TutorRegisterScreen from '../screens/auth/TutorRegisterScreen';
import TutorPairingScreen from '../screens/tutor/PairingScreen';
import TutorDashboardScreen from '../screens/tutor/DashboardScreen';
import LogoutScreen from '../screens/tutor/LogoutScreen';
import TutorAccountScreen from '../screens/tutor/TutorAccountScreen';
import AlertDetailScreen from '../screens/tutor/AlertDetailScreen';
import SeniorPairingScreen from '../screens/senior/PairingScreen';
import SeniorHomeScreen from '../screens/senior/HomeScreen';
import SeniorBlockScreen from '../screens/senior/BlockScreen';
import SeniorSettingsScreen from '../screens/senior/SeniorSettingsScreen';
import SeniorShareEmailScreen from '../screens/senior/ShareEmailScreen';
import VerifyEmailScreen from '../screens/auth/VerifyEmailScreen';
import SeniorSoloLoginScreen from '../screens/auth/SeniorSoloLoginScreen';
import SeniorSoloConsentScreen from '../screens/senior/SeniorSoloConsentScreen';
import SeniorSoloAlertsScreen from '../screens/senior/SeniorSoloAlertsScreen';

type SavedMode = 'senior' | 'tutor' | 'senior_solo' | null;

interface RootNavigatorProps {
  initialMode: SavedMode;
  hasDeviceId: boolean;
  hasConsent: boolean;
}

const Stack = createNativeStackNavigator<RootStackParamList>();

function getInitialRoute(mode: SavedMode, hasDeviceId: boolean, hasConsent: boolean): keyof RootStackParamList {
  if (mode === 'senior') return hasDeviceId ? 'SeniorHome' : 'SeniorPairing';
  if (mode === 'tutor') return 'TutorLogin';
  if (mode === 'senior_solo') return hasConsent ? 'SeniorHome' : 'SeniorSoloConsent';
  return 'Welcome';
}

export default function RootNavigator({ initialMode, hasDeviceId, hasConsent }: RootNavigatorProps) {
  return (
    <Stack.Navigator initialRouteName={getInitialRoute(initialMode, hasDeviceId, hasConsent)}>
      <Stack.Screen name="Welcome" component={WelcomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="ModeSelection" component={ModeSelectionScreen} options={{ headerShown: false }} />
      <Stack.Screen name="SeniorConsent" component={SeniorConsentScreen} options={{ title: 'Antes de continuar' }} />
      <Stack.Screen name="TutorLogin" component={TutorLoginScreen} options={{ headerShown: false }} />
      <Stack.Screen name="TutorRegister" component={TutorRegisterScreen} options={{ headerShown: false }} />
      <Stack.Screen name="TutorPairing" component={TutorPairingScreen} options={{ title: 'Vincular dispositivo' }} />
      <Stack.Screen name="TutorDashboard" component={TutorDashboardScreen} options={{ headerShown: false }} />
      <Stack.Screen name="TutorLogout" component={LogoutScreen} options={{ headerShown: false }} />
      <Stack.Screen name="TutorAccount" component={TutorAccountScreen} options={{ headerShown: false }} />
      <Stack.Screen name="AlertDetail" component={AlertDetailScreen} />
      <Stack.Screen name="SeniorPairing" component={SeniorPairingScreen} options={{ headerShown: false }} />
      <Stack.Screen name="SeniorHome" component={SeniorHomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="SeniorSettings" component={SeniorSettingsScreen} options={{ headerShown: false }} />
      <Stack.Screen
        name="SeniorBlock"
        component={SeniorBlockScreen}
        options={{ headerShown: false, gestureEnabled: false, animation: 'fade' }}
      />
      <Stack.Screen name="SeniorShareEmail" component={SeniorShareEmailScreen} options={{ headerShown: false }} />
      <Stack.Screen name="VerifyEmail" component={VerifyEmailScreen} options={{ headerShown: false }} />
      <Stack.Screen name="SeniorSoloLogin" component={SeniorSoloLoginScreen} options={{ headerShown: false }} />
      <Stack.Screen name="SeniorSoloConsent" component={SeniorSoloConsentScreen} options={{ headerShown: false, gestureEnabled: false }} />
      <Stack.Screen name="SeniorSoloAlerts" component={SeniorSoloAlertsScreen} options={{ headerShown: false }} />
    </Stack.Navigator>
  );
}
