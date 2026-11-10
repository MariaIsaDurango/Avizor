import { apiFetch } from './api';

interface Pairing {
  id: string;
  code: string;
  expires_at: string;
}

export async function createPairing(): Promise<Pairing> {
  const response = await apiFetch('/api/v1/pairings', { method: 'POST' });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al generar el código de vinculación.');
  }
  return response.json();
}
