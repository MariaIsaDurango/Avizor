import * as FileSystem from 'expo-file-system/legacy';
import { apiFetch, getToken } from './api';
import { API_BASE_URL } from '../constants/api';
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
  deviceId: string | null,
  inputType: InputType,
  value: string,
  options?: { channel?: 'manual' | 'screen' | 'sms'; origin?: 'manual' | 'automatic' },
): Promise<Verdict> {
  const body: Record<string, unknown> = {
    ...(deviceId ? { device_id: deviceId } : {}),
    channel: options?.channel ?? 'manual',
    origin: options?.origin ?? 'manual',
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

const MAX_FILE_BYTES = 10 * 1024 * 1024;

function attachmentType(mimeType: string): 'document' | 'image' {
  return mimeType === 'application/pdf' ? 'document' : 'image';
}

const MAX_POLL_ATTEMPTS = 24;

async function pollVerdict(analysisId: string, retryAfterMs: number): Promise<Verdict> {
  const delay = (ms: number) => new Promise<void>(resolve => setTimeout(resolve, ms));
  let interval = retryAfterMs;
  for (let i = 0; i < MAX_POLL_ATTEMPTS; i++) {
    await delay(interval);
    const res = await apiFetch(`/api/v1/analyses/${analysisId}/verdict`);
    if (res.status === 200) return res.json();
    if (res.status !== 202) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? 'Error al obtener el resultado.');
    }
    const body = await res.json().catch(() => ({}));
    interval = body.retry_after_ms ?? interval;
  }
  throw new Error('El análisis tardó demasiado. Inténtalo de nuevo.');
}

export async function submitAnalysisWithFile(
  deviceId: string | null,
  fileUri: string,
  mimeType: string,
): Promise<Verdict> {
  const ext = mimeType === 'application/pdf' ? 'pdf' : (mimeType.split('/')[1] ?? 'jpg');
  const cacheUri = `${FileSystem.cacheDirectory}attachment.${ext}`;
  await FileSystem.copyAsync({ from: fileUri, to: cacheUri });
  const fileResponse = await fetch(cacheUri);
  const blob = await fileResponse.blob();

  if (blob.size > MAX_FILE_BYTES) {
    throw new Error('El archivo supera los 10 MB. Prueba con un archivo más pequeño.');
  }

  const metadata = {
    ...(deviceId ? { device_id: deviceId } : {}),
    channel: 'manual',
    origin: 'manual',
    received_at: new Date().toISOString(),
    anonymization: { applied: true, ner_model_version: 'none', redacted_entities: [] },
    attachments: [{
      file_field: 'attachment_0',
      type: attachmentType(mimeType),
      mime: mimeType,
      size_bytes: blob.size,
    }],
  };

  const formData = new FormData();
  formData.append('metadata', JSON.stringify(metadata));
  formData.append('attachment_0', blob, `attachment.${ext}`);

  const token = await getToken();
  const response = await fetch(`${API_BASE_URL}/api/v1/analyses`, {
    method: 'POST',
    body: formData,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail ?? 'Error al analizar el archivo.');
  }

  if (response.status === 202) {
    const accepted = await response.json() as { analysis_id: string; retry_after_ms: number };
    return pollVerdict(accepted.analysis_id, accepted.retry_after_ms);
  }

  return response.json();
}

export async function getVerdict(analysisId: string): Promise<Verdict> {
  const response = await apiFetch(`/api/v1/analyses/${analysisId}/verdict`);
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al obtener el resultado del análisis.');
  }
  return response.json();
}
