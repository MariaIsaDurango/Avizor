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
import AlertDetailScreen from '../screens/tutor/AlertDetailScreen';
import SeniorHomeScreen from '../screens/senior/HomeScreen';

type SavedMode = 'senior' | 'tutor' | null;

interface RootNavigatorProps {
  initialMode: SavedMode;
}

const Stack = createNativeStackNavigator<RootStackParamList>();

function getInitialRoute(mode: SavedMode): keyof RootStackParamList {
  if (mode === 'senior') return 'SeniorHome';
  if (mode === 'tutor') return 'TutorLogin';
  return 'Welcome';
}

export default function RootNavigator({ initialMode }: RootNavigatorProps) {
  return (
    <Stack.Navigator initialRouteName={getInitialRoute(initialMode)}>
      <Stack.Screen name="Welcome" component={WelcomeScreen} options={{ headerShown: false }} />
      <Stack.Screen name="ModeSelection" component={ModeSelectionScreen} options={{ headerShown: false }} />
      <Stack.Screen name="SeniorConsent" component={SeniorConsentScreen} options={{ title: 'Antes de continuar' }} />
      <Stack.Screen name="TutorLogin" component={TutorLoginScreen} />
      <Stack.Screen name="TutorRegister" component={TutorRegisterScreen} />
      <Stack.Screen name="TutorPairing" component={TutorPairingScreen} />
      <Stack.Screen name="TutorDashboard" component={TutorDashboardScreen} options={{ headerShown: false }} />
      <Stack.Screen name="TutorLogout" component={LogoutScreen} options={{ title: 'Cerrar sesión' }} />
      <Stack.Screen name="AlertDetail" component={AlertDetailScreen} />
      <Stack.Screen name="SeniorHome" component={SeniorHomeScreen} options={{ headerShown: false }} />
    </Stack.Navigator>
  );
}
