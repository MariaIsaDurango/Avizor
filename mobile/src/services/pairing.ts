import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { apiFetch, saveToken } from './api';
import { STORAGE_KEYS } from '../constants/storage';

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
}

export async function redeemPairing(code: string): Promise<void> {
  const response = await apiFetch('/api/v1/pairings/redeem', {
    method: 'POST',
    body: JSON.stringify({
      code,
      device: {
        platform: Platform.OS as 'ios' | 'android',
        app_version: '1.0.0',
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
}

export async function createPairing(seniorDisplayName: string): Promise<Pairing> {
  const response = await apiFetch('/api/v1/pairings', {
    method: 'POST',
    body: JSON.stringify({ senior_display_name: seniorDisplayName }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al generar el código de vinculación.');
  }
  return response.json();
}
