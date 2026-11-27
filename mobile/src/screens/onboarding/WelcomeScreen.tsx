import { View, Text, Image, StyleSheet } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../navigation/types';
import Screen from '../../components/Screen';
import Button from '../../components/Button';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { useAccessibility } from '../../contexts/AccessibilityContext';

type Props = NativeStackScreenProps<RootStackParamList, 'Welcome'>;

export default function WelcomeScreen({ navigation }: Props) {
  const { largeText } = useAccessibility();

  return (
    <Screen style={styles.screen}>
      <View style={styles.hero}>
        <Image
          source={require('../../../assets/logo-web.png')}
          style={styles.heroImage}
          resizeMode="contain"
          accessibilityLabel="Avizor"
        />
        <Text style={[styles.logoText, largeText && { fontSize: 48 }]}>Avizor</Text>
        <Text style={[styles.tagline, largeText && { fontSize: 22 }]}>Protección digital para quien quieres</Text>
      </View>
      <Button
        label="Comenzar"
        onPress={() => navigation.navigate('ModeSelection')}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  screen: {
    justifyContent: 'space-between',
    paddingBottom: 40,
  },
  hero: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  heroImage: {
    width: 220,
    height: 220,
  },
  logoText: {
    fontSize: 42,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    letterSpacing: 1,
  },
  tagline: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.regular,
    color: colors.primary,
    textAlign: 'center',
  },
});
