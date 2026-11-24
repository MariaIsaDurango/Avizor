import { apiFetch } from './api';

export interface SummaryStats {
  period_days: number;
  total: number;
  by_threat_type: Record<string, number>;
  by_channel: Record<string, number>;
}

export async function getStatsSummary(periodDays: 7 | 30 | 90 = 7): Promise<SummaryStats> {
  const response = await apiFetch(`/api/v1/stats/summary?period=${periodDays}`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al obtener estadísticas.');
  }
  return response.json();
}
