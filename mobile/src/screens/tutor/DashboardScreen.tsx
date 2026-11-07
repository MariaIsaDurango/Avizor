import { View, Text, StyleSheet } from 'react-native';

export default function TutorDashboardScreen() {
  return (
    <View style={styles.container}>
      <Text>Panel de control Tutor</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
