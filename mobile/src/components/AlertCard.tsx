import { View, Text, StyleSheet } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { colors } from '../constants/colors';
import { fontSize, fontWeight } from '../constants/typography';
import { useAccessibility } from '../contexts/AccessibilityContext';

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

const RISK_COLORS_COLORBLIND: Record<RiskLevel, string> = {
  green: colors.successColorBlind,
  amber: colors.warning,
  red: colors.alert,
};

const RISK_LABELS: Record<RiskLevel, string> = {
  green: 'seguro',
  amber: 'sospechoso',
  red: 'peligro',
};

export default function AlertCard({ icon, title, description, riskLevel }: AlertCardProps) {
  const { largeText, colorBlind } = useAccessibility();
  const accentColor = (colorBlind ? RISK_COLORS_COLORBLIND : RISK_COLORS)[riskLevel];
  const bodySize = largeText ? fontSize.body * 1.3 : fontSize.body;
  const iconSize = largeText ? 36 : 28;

  return (
    <View
      style={[styles.card, { borderLeftColor: accentColor }]}
      accessible
      accessibilityLabel={`Alerta ${RISK_LABELS[riskLevel]}: ${title}. ${description}`}
    >
      <MaterialIcons name={icon} size={iconSize} color={accentColor} style={styles.icon} />
      <View style={styles.content}>
        <View style={styles.titleRow}>
          <Text style={[styles.title, { fontSize: bodySize }]}>{title}</Text>
          {colorBlind && (
            <Text style={[styles.riskBadge, { color: accentColor, fontSize: largeText ? 13 : 11 }]}>
              {RISK_LABELS[riskLevel].toUpperCase()}
            </Text>
          )}
        </View>
        <Text style={[styles.description, { fontSize: bodySize }]}>{description}</Text>
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
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  title: {
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  riskBadge: {
    fontWeight: fontWeight.bold,
    opacity: 0.8,
  },
  description: {
    color: colors.primary,
  },
});
