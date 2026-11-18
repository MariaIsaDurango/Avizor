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

export async function logout(): Promise<void> {
  await unregisterDevice().catch(() => {});
  await clearToken();
  await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_MODE);
}
