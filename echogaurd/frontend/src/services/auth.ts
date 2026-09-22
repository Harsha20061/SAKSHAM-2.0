import api from './api'

export interface SignupRequest {
  username: string
  display_name: string
  password: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface CurrentUser {
  id: string
  username: string
  display_name: string
}

export async function signup(
  data: SignupRequest,
) {
  const response = await api.post(
    '/auth/signup',
    data,
  )

  return response.data
}

export async function login(
  data: LoginRequest,
): Promise<TokenResponse> {
  const response = await api.post<TokenResponse>(
    '/auth/login',
    data,
  )

  return response.data
}

export async function getCurrentUser(): Promise<CurrentUser> {
  const response = await api.get<CurrentUser>(
    '/auth/me',
  )

  return response.data
}