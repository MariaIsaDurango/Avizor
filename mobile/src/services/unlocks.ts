import { apiFetch } from './api';

export type UnlockStatus = 'pending_guardian' | 'approved' | 'rejected' | 'expired';

export interface Unlock {
  id: string;
  analysis_id: string;
  status: UnlockStatus;
  requested_at: string;
  expires_at: string;
  resolved_by: string | null;
  resolved_at: string | null;
}

export async function createUnlock(analysisId: string): Promise<Unlock> {
  const response = await apiFetch('/api/v1/unlocks', {
    method: 'POST',
    body: JSON.stringify({ analysis_id: analysisId }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al solicitar el desbloqueo.');
  }
  return response.json();
}

export async function updateUnlock(
  unlockId: string,
  status: 'approved' | 'rejected',
): Promise<Unlock> {
  const response = await apiFetch(`/api/v1/unlocks/${unlockId}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al actualizar la solicitud de desbloqueo.');
  }
  return response.json();
}
