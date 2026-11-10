import { apiFetch } from './api';

export type InputType = 'text' | 'url' | 'phone_number';

export type BlockTemplate =
  | 'FAKE_DO_NOT_TOUCH'
  | 'DANGEROUS_LINK'
  | 'SUSPICIOUS_CALL'
  | 'ASKS_BANK_DETAILS'
  | 'LOOKS_SAFE'
  | 'UNSURE_CALL_FAMILY';

export interface Verdict {
  analysis_id: string;
  phase: 'fast' | 'agent';
  risk_level: 'green' | 'amber' | 'red';
  threat_type: string;
  action: 'allow' | 'silent_block' | 'block_and_alert';
  block_template: BlockTemplate | null;
  confidence: number;
  final: boolean;
  retry_after_ms: number | null;
  issued_at: string;
}

export async function submitAnalysis(
  deviceId: string,
  inputType: InputType,
  value: string,
): Promise<Verdict> {
  const body: Record<string, unknown> = {
    device_id: deviceId,
    channel: 'manual',
    origin: 'manual',
    input_type: inputType,
    received_at: new Date().toISOString(),
  };

  if (inputType === 'phone_number') {
    body.sender = { type: 'phone', value };
  } else {
    body.content = {
      text: value,
      ...(inputType === 'url' ? { urls: [value] } : {}),
      anonymization: {
        applied: true,
        // NER en dispositivo pendiente (Laura, issue #37); por ahora declaramos aplicado manualmente
        ner_model_version: 'ner-v0-manual',
      },
    };
  }

  const response = await apiFetch('/api/v1/analyses', {
    method: 'POST',
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al analizar el contenido.');
  }

  return response.json();
}
