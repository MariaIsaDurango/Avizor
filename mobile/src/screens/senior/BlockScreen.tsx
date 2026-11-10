import { View, Text, Pressable, StyleSheet, Linking } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import Screen from '../../components/Screen';
import { RootStackParamList } from '../../navigation/types';
import { BlockTemplate } from '../../services/analyses';
import { colors } from '../../constants/colors';
import { fontWeight } from '../../constants/typography';

type Props = NativeStackScreenProps<RootStackParamList, 'SeniorBlock'>;

type Config = {
  message: string;
  empathy: string;
  icon: keyof typeof MaterialIcons.glyphMap;
  background: string;
};

const CONFIGS: Record<BlockTemplate, Config> = {
  FAKE_DO_NOT_TOUCH: {
    message: '¡Cuidado! Este mensaje es falso.\nNo toques nada.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    icon: 'dangerous',
    background: colors.alert,
  },
  DANGEROUS_LINK: {
    message: 'Este enlace es peligroso.\nNo lo abras.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    icon: 'dangerous',
    background: colors.alert,
  },
  SUSPICIOUS_CALL: {
    message: 'Esta llamada puede ser una estafa.\nDesconfía.',
    empathy: 'No respondas. Estás protegido/a.',
    icon: 'warning',
    background: colors.alert,
  },
  ASKS_BANK_DETAILS: {
    message: 'Nunca des tus datos bancarios.\nEsto es un fraude.',
    empathy: 'Tranquilo/a, lo hemos bloqueado por ti.\nNo pasa nada.',
    icon: 'dangerous',
    background: colors.alert,
  },
  LOOKS_SAFE: {
    message: 'Este mensaje parece seguro.',
    empathy: '¡Todo bien! No hay nada de qué preocuparse.',
    icon: 'check-circle',
    background: colors.success,
  },
  UNSURE_CALL_FAMILY: {
    message: 'No estamos seguros.\nConsulta con tu familiar\nantes de hacer nada.',
    empathy: 'Es mejor preguntar cuando hay dudas.',
    icon: 'warning',
    background: colors.warning,
  },
};

export default function SeniorBlockScreen({ navigation, route }: Props) {
  const config = CONFIGS[route.params.template];

  return (
    <Screen style={{ backgroundColor: config.background }}>
      <View style={styles.content}>
        <MaterialIcons
          name={config.icon}
          size={96}
          color={colors.white}
          importantForAccessibility="no-hide-descendants"
          accessibilityElementsHidden
        />
        <Text style={styles.message}>{config.message}</Text>
        <Text style={styles.empathy}>{config.empathy}</Text>
      </View>

      <View style={styles.footer}>
        <Pressable
          style={styles.callButton}
          onPress={() => Linking.openURL('tel:')}
          accessibilityRole="button"
          accessibilityLabel="Llamar a tu familiar"
        >
          <MaterialIcons name="phone" size={28} color={colors.success} />
          <Text style={styles.callLabel}>Llamar a tu familiar</Text>
        </Pressable>

        <Pressable
          style={styles.dismissButton}
          onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel="Estoy protegida, gracias"
        >
          <Text style={styles.dismissLabel}>Estoy protegido/a, gracias</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 24,
  },
  message: {
    fontSize: 28,
    fontWeight: fontWeight.bold,
    color: colors.white,
    textAlign: 'center',
    lineHeight: 38,
  },
  empathy: {
    fontSize: 20,
    color: colors.white,
    textAlign: 'center',
    opacity: 0.9,
    lineHeight: 28,
  },
  footer: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 20,
    gap: 12,
    marginBottom: 8,
  },
  callButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    backgroundColor: '#E8F5E9',
    borderRadius: 12,
    paddingVertical: 18,
    paddingHorizontal: 20,
  },
  callLabel: {
    fontSize: 22,
    fontWeight: fontWeight.bold,
    color: colors.success,
  },
  dismissButton: {
    alignItems: 'center',
    paddingVertical: 14,
  },
  dismissLabel: {
    fontSize: 18,
    color: colors.primary,
    opacity: 0.7,
  },
});
