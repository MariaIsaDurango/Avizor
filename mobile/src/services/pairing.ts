import { apiFetch } from './api';

interface Pairing {
  id: string;
  code: string;
  expires_at: string;
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
