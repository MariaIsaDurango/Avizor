import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { RootStackParamList } from './types';
import ModeSelectionScreen from '../screens/onboarding/ModeSelectionScreen';
import TutorLoginScreen from '../screens/auth/TutorLoginScreen';
import TutorRegisterScreen from '../screens/auth/TutorRegisterScreen';
import TutorPairingScreen from '../screens/tutor/PairingScreen';
import TutorDashboardScreen from '../screens/tutor/DashboardScreen';
import AlertDetailScreen from '../screens/tutor/AlertDetailScreen';
import SeniorHomeScreen from '../screens/senior/HomeScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

export default function RootNavigator() {
  return (
    <Stack.Navigator initialRouteName="ModeSelection">
      <Stack.Screen
        name="ModeSelection"
        component={ModeSelectionScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen name="TutorLogin" component={TutorLoginScreen} />
      <Stack.Screen name="TutorRegister" component={TutorRegisterScreen} />
      <Stack.Screen name="TutorPairing" component={TutorPairingScreen} />
      <Stack.Screen
        name="TutorDashboard"
        component={TutorDashboardScreen}
        options={{ headerShown: false }}
      />
      <Stack.Screen name="AlertDetail" component={AlertDetailScreen} />
      <Stack.Screen
        name="SeniorHome"
        component={SeniorHomeScreen}
        options={{ headerShown: false }}
      />
    </Stack.Navigator>
  );
}
