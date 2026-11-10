import { apiFetch, saveToken, clearToken } from './api';

interface RegisterData {
  name: string;
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

export async function register(data: RegisterData): Promise<void> {
  const response = await apiFetch('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail ?? 'Error al registrarse.');
  }

  const result: TokenResponse = await response.json();
  await saveToken(result.access_token);
}

export async function login(data: LoginData): Promise<void> {
  const response = await apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error('Credenciales incorrectas. Verifica tu email y contraseña.');
  }

  const result: TokenResponse = await response.json();
  await saveToken(result.access_token);
}

export async function logout(): Promise<void> {
  await clearToken();
}
