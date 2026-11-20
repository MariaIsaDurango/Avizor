import { useEffect, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { MaterialIcons } from '@expo/vector-icons';
import Screen from '../../components/Screen';
import { colors } from '../../constants/colors';
import { fontSize, fontWeight } from '../../constants/typography';
import { getMe, updateMe, changePassword, logout } from '../../services/auth';
import { unlinkSenior, getSenior, updateSeniorPhone } from '../../services/pairing';
import { RootStackParamList } from '../../navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'TutorAccount'>;

export default function TutorAccountScreen({ navigation }: Props) {
  const [loading, setLoading] = useState(true);
  const [displayName, setDisplayName] = useState('');
  const [originalName, setOriginalName] = useState('');
  const [email, setEmail] = useState('');
  const [nameSaving, setNameSaving] = useState(false);
  const [nameError, setNameError] = useState('');

  const [phone, setPhone] = useState('');
  const [originalPhone, setOriginalPhone] = useState('');
  const [hasSenior, setHasSenior] = useState(false);
  const [phoneSaving, setPhoneSaving] = useState(false);
  const [phoneError, setPhoneError] = useState('');

  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [pwdSaving, setPwdSaving] = useState(false);
  const [pwdError, setPwdError] = useState('');

  useEffect(() => {
    Promise.all([getMe(), getSenior()])
      .then(([me, senior]) => {
        setDisplayName(me.display_name);
        setOriginalName(me.display_name);
        setEmail(me.email ?? '');
        if (senior) {
          setHasSenior(true);
          setPhone(senior.guardian_phone ?? '');
          setOriginalPhone(senior.guardian_phone ?? '');
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  async function handleSaveName() {
    const trimmed = displayName.trim();
    if (!trimmed) { setNameError('El nombre no puede estar vacío.'); return; }
    setNameSaving(true);
    setNameError('');
    try {
      await updateMe(trimmed);
      setOriginalName(trimmed);
      setDisplayName(trimmed);
    } catch (e) {
      setNameError(e instanceof Error ? e.message : 'Error al guardar.');
    } finally {
      setNameSaving(false);
    }
  }

  async function handleSavePhone() {
    setPhoneSaving(true);
    setPhoneError('');
    try {
      await updateSeniorPhone(phone.trim() || null);
      setOriginalPhone(phone.trim());
    } catch (e) {
      setPhoneError(e instanceof Error ? e.message : 'Error al guardar.');
    } finally {
      setPhoneSaving(false);
    }
  }

  async function handleChangePassword() {
    if (newPwd !== confirmPwd) { setPwdError('Las contraseñas no coinciden.'); return; }
    if (newPwd.length < 10) { setPwdError('La nueva contraseña debe tener al menos 10 caracteres.'); return; }
    setPwdSaving(true);
    setPwdError('');
    try {
      await changePassword(currentPwd, newPwd);
      await logout();
      navigation.reset({ index: 0, routes: [{ name: 'TutorLogin' }] });
    } catch (e) {
      setPwdError(e instanceof Error ? e.message : 'Error al cambiar la contraseña.');
      setPwdSaving(false);
    }
  }

  function handleUnlinkSenior() {
    Alert.alert(
      '¿Desvincular sénior?',
      'El sénior dejará de estar protegido por Avizor. Esta acción no se puede deshacer.',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Desvincular',
          style: 'destructive',
          onPress: async () => {
            try {
              await unlinkSenior();
              navigation.reset({ index: 0, routes: [{ name: 'TutorPairing' }] });
            } catch (e) {
              Alert.alert('Error', e instanceof Error ? e.message : 'No se pudo desvincular.');
            }
          },
        },
      ],
    );
  }

  if (loading) {
    return (
      <Screen style={styles.centered}>
        <ActivityIndicator size="large" color={colors.primary} />
      </Screen>
    );
  }

  const nameChanged = displayName.trim() !== originalName;

  return (
    <Screen scrollable>
      <View style={styles.header}>
        <Pressable onPress={() => navigation.goBack()} style={styles.backBtn} accessibilityRole="button" accessibilityLabel="Volver">
          <MaterialIcons name="arrow-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.title}>Mi cuenta</Text>
        <View style={{ width: 40 }} />
      </View>

      {/* Perfil */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Perfil</Text>

        <Text style={styles.fieldLabel}>Nombre</Text>
        <TextInput
          style={styles.input}
          value={displayName}
          onChangeText={(t) => { setDisplayName(t); setNameError(''); }}
          autoCapitalize="words"
          maxLength={50}
          returnKeyType="done"
          onSubmitEditing={nameChanged ? handleSaveName : undefined}
        />
        {nameError !== '' && <Text style={styles.fieldError}>{nameError}</Text>}
        {nameChanged && (
          <Pressable
            style={[styles.saveBtn, nameSaving && styles.saveBtnDisabled]}
            onPress={handleSaveName}
            disabled={nameSaving}
            accessibilityRole="button"
          >
            <Text style={styles.saveBtnText}>{nameSaving ? 'Guardando…' : 'Guardar nombre'}</Text>
          </Pressable>
        )}

        {email !== '' && (
          <>
            <Text style={[styles.fieldLabel, { marginTop: 16 }]}>Email</Text>
            <Text style={styles.emailText}>{email}</Text>
          </>
        )}

        {hasSenior && (
          <>
            <Text style={[styles.fieldLabel, { marginTop: 16 }]}>
              Tu teléfono{' '}
              <Text style={{ fontWeight: '400', opacity: 0.6 }}>(para llamadas del Sénior)</Text>
            </Text>
            <TextInput
              style={styles.input}
              value={phone}
              onChangeText={(t) => { setPhone(t); setPhoneError(''); }}
              keyboardType="phone-pad"
              placeholder="+34 600 000 000"
              maxLength={30}
              returnKeyType="done"
              onSubmitEditing={phone.trim() !== originalPhone ? handleSavePhone : undefined}
            />
            {phoneError !== '' && <Text style={styles.fieldError}>{phoneError}</Text>}
            {phone.trim() !== originalPhone && (
              <Pressable
                style={[styles.saveBtn, phoneSaving && styles.saveBtnDisabled]}
                onPress={handleSavePhone}
                disabled={phoneSaving}
                accessibilityRole="button"
              >
                <Text style={styles.saveBtnText}>{phoneSaving ? 'Guardando…' : 'Guardar teléfono'}</Text>
              </Pressable>
            )}
          </>
        )}
      </View>

      {/* Seguridad */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Seguridad</Text>
        <Pressable
          style={styles.row}
          onPress={() => { setShowPasswordForm((v) => !v); setPwdError(''); }}
          accessibilityRole="button"
          accessibilityLabel="Cambiar contraseña"
        >
          <Text style={styles.rowLabel}>Cambiar contraseña</Text>
          <MaterialIcons
            name={showPasswordForm ? 'keyboard-arrow-up' : 'keyboard-arrow-right'}
            size={20}
            color={colors.primary}
            style={{ opacity: 0.5 }}
          />
        </Pressable>

        {showPasswordForm && (
          <View style={styles.passwordForm}>
            <TextInput
              style={styles.input}
              placeholder="Contraseña actual"
              secureTextEntry
              value={currentPwd}
              onChangeText={(t) => { setCurrentPwd(t); setPwdError(''); }}
              autoComplete="current-password"
            />
            <TextInput
              style={[styles.input, { marginTop: 8 }]}
              placeholder="Nueva contraseña (mín. 10 caracteres)"
              secureTextEntry
              value={newPwd}
              onChangeText={(t) => { setNewPwd(t); setPwdError(''); }}
              autoComplete="new-password"
            />
            <TextInput
              style={[styles.input, { marginTop: 8 }]}
              placeholder="Confirmar nueva contraseña"
              secureTextEntry
              value={confirmPwd}
              onChangeText={(t) => { setConfirmPwd(t); setPwdError(''); }}
              autoComplete="new-password"
            />
            {pwdError !== '' && <Text style={styles.fieldError}>{pwdError}</Text>}
            <Pressable
              style={[styles.saveBtn, pwdSaving && styles.saveBtnDisabled, { marginTop: 12 }]}
              onPress={handleChangePassword}
              disabled={pwdSaving}
              accessibilityRole="button"
            >
              <Text style={styles.saveBtnText}>{pwdSaving ? 'Guardando…' : 'Cambiar contraseña'}</Text>
            </Pressable>
            <Text style={styles.pwdHint}>Al cambiar la contraseña se cerrará la sesión en todos los dispositivos.</Text>
          </View>
        )}
      </View>

      {/* Acciones destructivas */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Zona de peligro</Text>
        <Pressable
          style={styles.dangerRow}
          onPress={handleUnlinkSenior}
          accessibilityRole="button"
          accessibilityLabel="Desvincular sénior"
        >
          <MaterialIcons name="link-off" size={20} color={colors.alert} />
          <Text style={styles.dangerText}>Desvincular sénior</Text>
        </Pressable>

        <View style={styles.divider} />

        <Pressable
          style={styles.dangerRow}
          onPress={() => navigation.navigate('TutorLogout')}
          accessibilityRole="button"
          accessibilityLabel="Cerrar sesión"
        >
          <MaterialIcons name="logout" size={20} color={colors.alert} />
          <Text style={styles.dangerText}>Cerrar sesión</Text>
        </Pressable>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
    marginBottom: 24,
  },
  backBtn: { width: 40, alignItems: 'flex-start' },
  title: {
    fontSize: 20,
    fontWeight: fontWeight.bold,
    color: colors.primary,
  },
  section: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    opacity: 0.6,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginBottom: 12,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: fontWeight.bold,
    color: colors.primary,
    marginBottom: 6,
  },
  input: {
    borderWidth: 1.5,
    borderColor: '#d4d4d8',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: fontSize.body,
    color: colors.primary,
    backgroundColor: colors.background,
  },
  fieldError: {
    fontSize: 13,
    color: colors.alert,
    marginTop: 4,
  },
  emailText: {
    fontSize: fontSize.body,
    color: colors.primary,
    opacity: 0.6,
    paddingVertical: 4,
  },
  saveBtn: {
    backgroundColor: colors.primary,
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    marginTop: 10,
  },
  saveBtnDisabled: { opacity: 0.6 },
  saveBtnText: {
    color: colors.white,
    fontWeight: fontWeight.bold,
    fontSize: fontSize.body,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
  },
  rowLabel: {
    fontSize: fontSize.body,
    color: colors.primary,
    fontWeight: fontWeight.bold,
  },
  passwordForm: {
    marginTop: 8,
  },
  pwdHint: {
    fontSize: 12,
    color: colors.primary,
    opacity: 0.5,
    marginTop: 8,
  },
  dangerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 10,
  },
  dangerText: {
    fontSize: fontSize.body,
    color: colors.alert,
    fontWeight: fontWeight.bold,
  },
  divider: {
    height: 1,
    backgroundColor: colors.primary,
    opacity: 0.08,
    marginVertical: 2,
  },
});
