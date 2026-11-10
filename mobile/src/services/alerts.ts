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

export interface Alert {
  id: string;
  analysis_id: string;
  senior_id: string;
  senior_name: string;
  risk_level: 'red';
  threat_type: ThreatType;
  channel: Channel;
  summary: string;
  status: AlertStatus;
  created_at: string;
}

export interface AlertPage {
  items: Alert[];
  next_cursor: string | null;
}

export async function getAlerts(cursor?: string): Promise<AlertPage> {
  const url = cursor ? `/api/v1/alerts?cursor=${cursor}` : '/api/v1/alerts';
  const response = await apiFetch(url);
  if (!response.ok) {
    throw new Error('Error al cargar las alertas.');
  }
  return response.json();
}
