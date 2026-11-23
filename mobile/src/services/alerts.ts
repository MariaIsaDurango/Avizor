import { apiFetch } from './api';

export type ThreatType =
  | 'phishing'
  | 'smishing'
  | 'vishing'
  | 'spam'
  | 'identity_theft'
  | 'bank_fraud'
  | 'other'
  | 'none';

export type Channel = 'sms' | 'notification' | 'screen' | 'call' | 'manual';
export type AlertStatus = 'new' | 'seen' | 'confirmed_fraud' | 'false_positive';
export type IndicatorType = 'domain' | 'url' | 'phone' | 'alphanumeric_sender';
export type RagSource = 'incibe' | 'osi' | 'policia_nacional';

export interface IndicatorEvidence {
  type: IndicatorType;
  value: string;
  reason: string;
}

export interface OfficialNoticeEvidence {
  type: 'official_notice';
  source: RagSource;
  url: string;
}

export type Evidence = IndicatorEvidence | OfficialNoticeEvidence;

export interface Alert {
  id: string;
  analysis_id: string;
  senior_id: string;
  senior_name: string;
  risk_level: 'red';
  threat_type: ThreatType;
  channel: Channel;
  summary: string;
  explanation: string;
  evidence: Evidence[];
  status: AlertStatus;
  created_at: string;
}

export interface AlertPage {
  items: Alert[];
  next_cursor: string | null;
}

export async function getAlerts(cursor?: string): Promise<AlertPage> {
  const url = cursor
    ? `/api/v1/alerts?cursor=${encodeURIComponent(cursor)}`
    : '/api/v1/alerts';
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error('Error al cargar las alertas.');
  }
  return response.json();
}

export async function getAlert(alertId: string): Promise<Alert> {
  const response = await apiFetch(`/api/v1/alerts/${alertId}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al cargar la alerta.');
  }
  return response.json();
}

export async function updateAlert(alertId: string, status: Exclude<AlertStatus, 'new'>): Promise<Alert> {
  const response = await apiFetch(`/api/v1/alerts/${alertId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al actualizar la alerta.');
  }
  return response.json();
}
