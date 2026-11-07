import { View, Text, StyleSheet } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { colors } from '../constants/colors';
import { fontSize, fontWeight } from '../constants/typography';

export type RiskLevel = 'green' | 'amber' | 'red';

interface AlertCardProps {
  icon: keyof typeof MaterialIcons.glyphMap;
  title: string;
  description: string;
  riskLevel: RiskLevel;
}

const RISK_COLORS: Record<RiskLevel, string> = {
  green: colors.success,
  amber: colors.warning,
  red: colors.alert,
};

export default function AlertCard({ icon, title, description, riskLevel }: AlertCardProps) {
  const accentColor = RISK_COLORS[riskLevel];

  return (
    <View
      style={[styles.card, { borderLeftColor: accentColor }]}
      accessible
      accessibilityLabel={`Alerta ${riskLevel}: ${title}. ${description}`}
    >
      <MaterialIcons name={icon} size={28} color={accentColor} style={styles.icon} />
      <View style={styles.content}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.description}>{description}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    borderRadius: 8,
    borderLeftWidth: 5,
    padding: 16,
    alignItems: 'flex-start',
  },
  icon: {
    marginRight: 12,
    marginTop: 2,
  },
  content: {
    flex: 1,
  },
  title: {
    fontSize: fontSize.body,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginBottom: 4,
  },
  description: {
    fontSize: fontSize.body,
    color: colors.primary,
  },
});
