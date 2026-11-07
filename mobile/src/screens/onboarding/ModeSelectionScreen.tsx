import { View, Text, StyleSheet } from 'react-native';

export default function ModeSelectionScreen() {
  return (
    <View style={styles.container}>
      <Text>Selección de modo</Text>
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
