import { apiFetch } from './api';
import { STORAGE_KEYS, CONSENT_TEXT_VERSION } from '../constants/storage';
import * as SecureStore from 'expo-secure-store';

export type ConsentChannel = 'sms' | 'notification' | 'screen' | 'call' | 'manual';

const ALL_CHANNELS: ConsentChannel[] = ['sms', 'notification', 'screen', 'call', 'manual'];

export async function createSelfConsent(): Promise<void> {
  const seniorId = await SecureStore.getItemAsync(STORAGE_KEYS.SENIOR_ID);
  if (!seniorId) throw new Error('No se encontró el identificador del dispositivo.');

  const response = await apiFetch('/api/v1/consents', {
    method: 'POST',
    body: JSON.stringify({
      senior_id: seniorId,
      type: 'self',
      scope: ALL_CHANNELS,
      text_version: CONSENT_TEXT_VERSION,
      granted_by: seniorId,
      evidence: null,
      granted_at: new Date().toISOString(),
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al registrar el consentimiento.');
  }
}
