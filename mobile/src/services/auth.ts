import { Platform } from 'react-native';
import Constants from 'expo-constants';
import * as SecureStore from 'expo-secure-store';
import { apiFetch, saveToken, clearToken } from './api';
import { STORAGE_KEYS, CONSENT_TEXT_VERSION } from '../constants/storage';
import { unregisterDevice } from './devices';

interface RegisterData {
  display_name: string;
  email: string;
  password: string;
}

interface LoginData {
  email: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in?: number;
  device_id?: string;
}

export class EmailNotVerifiedError extends Error {
  constructor(public readonly email: string) {
    super('EMAIL_NOT_VERIFIED');
  }
}

export async function register(data: RegisterData): Promise<void> {
  const response = await apiFetch('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al registrarse.');
  }
}

export async function login(data: LoginData): Promise<void> {
  const response = await apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (response.status === 403) {
    throw new EmailNotVerifiedError(data.email);
  }

  if (!response.ok) {
    throw new Error('Credenciales incorrectas. Verifica tu email y contraseña.');
  }

  const result: TokenResponse = await response.json();
  await saveToken(result.access_token);
  if (result.expires_in) {
    const expiresAt = Date.now() + result.expires_in * 1000;
    await SecureStore.setItemAsync(STORAGE_KEYS.TOKEN_EXPIRES_AT, String(expiresAt));
  }
  await SecureStore.setItemAsync(STORAGE_KEYS.USER_MODE, 'tutor');
}

export async function verifyEmail(email: string, code: string): Promise<void> {
  const response = await apiFetch('/api/v1/auth/verify-email', {
    method: 'POST',
    body: JSON.stringify({ email, code }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Código incorrecto. Inténtalo de nuevo.');
  }
}

export async function resendVerification(email: string): Promise<void> {
  await apiFetch('/api/v1/auth/resend-verification', {
    method: 'POST',
    body: JSON.stringify({ email }),
  });
}

export async function getMe(): Promise<{ id: string; display_name: string; email: string | null; phone: string | null }> {
  const response = await apiFetch('/api/v1/auth/me');
  if (!response.ok) throw new Error('Error al obtener el perfil.');
  return response.json();
}

export async function updateMe(displayName: string, phone?: string | null): Promise<void> {
  const body: Record<string, unknown> = { display_name: displayName };
  if (phone !== undefined) body.phone = phone || null;
  const response = await apiFetch('/api/v1/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al actualizar el perfil.');
  }
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  const response = await apiFetch('/api/v1/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al cambiar la contraseña.');
  }
}

export async function isTokenExpired(): Promise<boolean> {
  const raw = await SecureStore.getItemAsync(STORAGE_KEYS.TOKEN_EXPIRES_AT);
  if (!raw) return false;
  return Date.now() > Number(raw);
}

export async function registerSeniorSolo(data: Omit<RegisterData, 'role'>): Promise<void> {
  const response = await apiFetch('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      ...data,
      role: 'senior_solo',
      device: {
        platform: Platform.OS,
        app_version: Constants.expoConfig?.version ?? '1.0.0',
      },
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al registrarse.');
  }
}

export async function loginSeniorSolo(data: LoginData): Promise<void> {
  const response = await apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (response.status === 403) {
    throw new EmailNotVerifiedError(data.email);
  }

  if (!response.ok) {
    throw new Error('Credenciales incorrectas. Verifica tu email y contraseña.');
  }

  const result: TokenResponse = await response.json();
  await saveToken(result.access_token);
  if (result.expires_in) {
    const expiresAt = Date.now() + result.expires_in * 1000;
    await SecureStore.setItemAsync(STORAGE_KEYS.TOKEN_EXPIRES_AT, String(expiresAt));
  }
  await SecureStore.setItemAsync(STORAGE_KEYS.USER_MODE, 'senior_solo');

  if (result.device_id) {
    const isFirstLogin = !(await SecureStore.getItemAsync(STORAGE_KEYS.DEVICE_ID));
    await SecureStore.setItemAsync(STORAGE_KEYS.DEVICE_ID, result.device_id);
    if (isFirstLogin) {
      try {
        const me = await getMe();
        await apiFetch('/api/v1/consents', {
          method: 'POST',
          body: JSON.stringify({
            senior_id: me.id,
            type: 'self',
            scope: ['sms', 'notification', 'screen'],
            text_version: CONSENT_TEXT_VERSION,
            granted_by: me.id,
            granted_at: new Date().toISOString(),
          }),
        });
      } catch {}
    }
  }
}

export async function logout(): Promise<void> {
  await unregisterDevice().catch(() => {});
  await clearToken();
  await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_MODE);
  await SecureStore.deleteItemAsync(STORAGE_KEYS.TOKEN_EXPIRES_AT).catch(() => {});
}
