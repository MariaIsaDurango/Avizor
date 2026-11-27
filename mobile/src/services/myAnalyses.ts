import { apiFetch } from './api';
import type { ThreatType, BlockTemplate } from './analyses';

export type RiskLevel = 'green' | 'amber' | 'red';

export type { ThreatType };

export type Channel = 'sms' | 'notification' | 'screen' | 'call' | 'manual';

export interface MyAnalysis {
  analysis_id: string;
  risk_level: RiskLevel;
  threat_type: ThreatType;
  channel: Channel;
  block_template: BlockTemplate | null;
  created_at: string;
}

export interface MyAnalysesPage {
  items: MyAnalysis[];
  total: number;
  limit: number;
  offset: number;
}

export async function getMyAnalyses(offset = 0, limit = 20): Promise<MyAnalysesPage> {
  const response = await apiFetch(`/api/v1/my-analyses?limit=${limit}&offset=${offset}`);
  if (!response.ok) throw new Error('Error al cargar el historial.');
  return response.json();
}
