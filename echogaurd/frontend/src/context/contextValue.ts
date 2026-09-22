import { createContext, type ReactNode } from 'react'
import type { CurrentUser } from '../services/auth'

export interface AuthContextValue {
  user: CurrentUser | null
  loading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
)

export type AuthProviderProps = {
  children: ReactNode
}
