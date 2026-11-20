import * as SecureStore from 'expo-secure-store';
import { apiFetch, saveToken, clearToken } from './api';
import { STORAGE_KEYS } from '../constants/storage';
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

export async function getMe(): Promise<{ id: string; display_name: string; email: string | null }> {
  const response = await apiFetch('/api/v1/auth/me');
  if (!response.ok) throw new Error('Error al obtener el perfil.');
  return response.json();
}

export async function updateMe(displayName: string): Promise<void> {
  const response = await apiFetch('/api/v1/auth/me', {
    method: 'PATCH',
    body: JSON.stringify({ display_name: displayName }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al actualizar el nombre.');
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

export async function logout(): Promise<void> {
  await unregisterDevice().catch(() => {});
  await clearToken();
  await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_MODE);
  await SecureStore.deleteItemAsync(STORAGE_KEYS.TOKEN_EXPIRES_AT).catch(() => {});
}
