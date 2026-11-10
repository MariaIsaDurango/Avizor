import { apiFetch } from './api';
import { anonymize, toE164, NER_MODEL_VERSION } from './anonymize';

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

function normalizeUrl(input: string): string {
  return input.startsWith('http') ? input : `https://${input}`;
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
    const e164 = toE164(value);
    if (!e164) throw new Error('Revisa el número. Usa el formato +34 600 000 000.');
    body.sender = { type: 'phone', value: e164 };
  } else {
    const rawText = inputType === 'url' ? normalizeUrl(value) : value;
    const { text: anonText, entities } = anonymize(rawText);
    body.content = {
      text: anonText,
      ...(inputType === 'url' ? { urls: [rawText] } : {}),
      anonymization: {
        applied: true,
        ner_model_version: NER_MODEL_VERSION,
        redacted_entities: entities,
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
