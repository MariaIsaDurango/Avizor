import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import Constants from 'expo-constants';
import { apiFetch, saveToken } from './api';
import { STORAGE_KEYS } from '../constants/storage';

export interface AccessibilityProfile {
  color_blindness: boolean;
  low_vision: boolean;
  blindness: boolean;
  hearing_impairment: boolean;
}

interface Pairing {
  id: string;
  code: string;
  expires_at: string;
}

interface RedeemResponse {
  access_token: string;
  token_type: 'bearer';
  device_id: string;
  senior_id: string;
  accessibility_profile: AccessibilityProfile | null;
  guardian_phone: string | null;
}

export interface SeniorProfile {
  display_name: string;
  accessibility_profile: AccessibilityProfile | null;
  guardian_phone: string | null;
}

export async function redeemPairing(code: string): Promise<void> {
  const response = await apiFetch('/api/v1/pairings/redeem', {
    method: 'POST',
    body: JSON.stringify({
      code,
      device: {
        platform: Platform.OS as 'ios' | 'android',
        app_version: Constants.expoConfig?.version ?? '1.0.0',
        push_token: null,
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Código incorrecto o caducado. Pide uno nuevo a tu familiar.');
  }

  const data: RedeemResponse = await response.json();
  await saveToken(data.access_token);
  await SecureStore.setItemAsync(STORAGE_KEYS.DEVICE_ID, data.device_id);
  await SecureStore.setItemAsync(STORAGE_KEYS.SENIOR_ID, data.senior_id);
  if (data.accessibility_profile) {
    await SecureStore.setItemAsync(
      STORAGE_KEYS.ACCESSIBILITY_PROFILE,
      JSON.stringify(data.accessibility_profile),
    );
  } else {
    await SecureStore.deleteItemAsync(STORAGE_KEYS.ACCESSIBILITY_PROFILE).catch(() => {});
  }
  if (data.guardian_phone) {
    await SecureStore.setItemAsync(STORAGE_KEYS.GUARDIAN_PHONE, data.guardian_phone);
  } else {
    await SecureStore.deleteItemAsync(STORAGE_KEYS.GUARDIAN_PHONE).catch(() => {});
  }
}

export async function createPairing(
  seniorDisplayName: string,
  accessibilityProfile?: AccessibilityProfile,
  guardianPhone?: string,
): Promise<Pairing> {
  const body: Record<string, unknown> = { senior_display_name: seniorDisplayName };
  if (accessibilityProfile) {
    body.senior_accessibility_profile = accessibilityProfile;
  }
  if (guardianPhone) {
    body.guardian_phone = guardianPhone;
  }
  const response = await apiFetch('/api/v1/pairings', {
    method: 'POST',
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al generar el código de vinculación.');
  }
  return response.json();
}

export async function unlinkSenior(): Promise<void> {
  const response = await apiFetch('/api/v1/senior', { method: 'DELETE' });
  if (!response.ok && response.status !== 404) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al desvincular al Sénior.');
  }
}

export async function getSeniorProfile(): Promise<SeniorProfile> {
  const response = await apiFetch('/api/v1/senior/me');
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al obtener el perfil del Sénior.');
  }
  return response.json();
}

export interface GuardianSeniorInfo {
  senior_display_name: string;
  guardian_phone: string | null;
}

export async function getSenior(): Promise<GuardianSeniorInfo | null> {
  const response = await apiFetch('/api/v1/senior');
  if (response.status === 404) return null;
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al obtener el Sénior.');
  }
  return response.json();
}

export async function updateSeniorPhone(phone: string | null): Promise<void> {
  const response = await apiFetch('/api/v1/senior/phone', {
    method: 'PATCH',
    body: JSON.stringify({ guardian_phone: phone }),
  });
  if (!response.ok) {
    const error = await response.json();
    const detail = Array.isArray(error.detail)
      ? 'Teléfono no válido. Ejemplo: +34 600 000 000'
      : error.detail;
    throw new Error(detail ?? 'Error al guardar el teléfono.');
  }
}
