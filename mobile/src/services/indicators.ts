import { apiFetch } from './api';
import { toE164 } from './anonymize';

export type IndicatorThreatType =
  | 'spam'
  | 'vishing'
  | 'smishing'
  | 'bank_fraud'
  | 'identity_theft'
  | 'other';

export interface IndicatorReport {
  type: 'phone';
  public_value: string;
  threat_type: IndicatorThreatType;
  counted: boolean;
}

export async function reportPhoneIndicator(
  deviceId: string | null,
  phoneNumber: string,
  threatType: IndicatorThreatType = 'spam',
): Promise<IndicatorReport> {
  const e164 = toE164(phoneNumber);
  const value = e164 ?? phoneNumber;

  const response = await apiFetch('/api/v1/indicators', {
    method: 'POST',
    body: JSON.stringify({
      type: 'phone',
      value,
      threat_type: threatType,
      ...(deviceId ? { device_id: deviceId } : {}),
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail ?? 'No se pudo reportar el número.');
  }

  return response.json();
}
