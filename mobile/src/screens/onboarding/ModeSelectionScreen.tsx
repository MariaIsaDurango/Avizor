import { View, Text, Image, Pressable, StyleSheet, useWindowDimensions } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { useAccessibility } from '../../contexts/AccessibilityContext';

type Props = NativeStackScreenProps<RootStackParamList, 'ModeSelection'>;

export default function ModeSelectionScreen({ navigation }: Props) {
  const { height } = useWindowDimensions();
  const { largeText } = useAccessibility();
  const logoSize = height < 700 ? 72 : 100;

  return (
    <Screen scrollable style={styles.screen}>
      <Text style={[styles.title, largeText && { fontSize: 32 }]}>Bienvenido a Avizor</Text>
      <Image
        source={require('../../../assets/logo-web.png')}
        style={[styles.logo, { width: logoSize, height: logoSize }]}
        resizeMode="contain"
        accessibilityLabel=""
      />
      <View style={styles.options}>
        <Pressable
          style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
          onPress={() => navigation.navigate('SeniorConsent')}
          accessibilityRole="button"
          accessibilityLabel="Vincular con PIN, modo Sénior"
        >
          <MaterialIcons name="shield" size={44} color={colors.primary} />
          <Text style={[styles.cardTitle, largeText && { fontSize: 28 }]}>Vincular con PIN</Text>
          <Text style={[styles.cardSubtitle, largeText && { fontSize: 22 }]}>Voy a introducir el código que me dio mi familiar</Text>
        </Pressable>

        <Pressable
          style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
          onPress={() => navigation.navigate('TutorLogin')}
          accessibilityRole="button"
          accessibilityLabel="Iniciar sesión o registrarse, modo Tutor"
        >
          <MaterialIcons name="favorite" size={44} color={colors.primary} />
          <Text style={[styles.cardTitle, largeText && { fontSize: 28 }]}>Iniciar sesión / Registro</Text>
          <Text style={[styles.cardSubtitle, largeText && { fontSize: 22 }]}>Gestiona tu protección o la de alguien cercano</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    paddingTop: 40,
  },
  title: {
    fontSize: fontSize.heading,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginBottom: 16,
    textAlign: 'center',
  },
  logo: {
    alignSelf: 'center',
    marginBottom: 20,
  },
  options: {
    gap: 20,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: colors.primary,
    padding: 28,
    alignItems: 'center',
    gap: 10,
  },
  cardPressed: {
    opacity: 0.75,
  },
  cardTitle: {
    fontSize: fontSize.button,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    textAlign: 'center',
  },
  cardSubtitle: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.regular,
    color: colors.primary,
    textAlign: 'center',
  },
});
