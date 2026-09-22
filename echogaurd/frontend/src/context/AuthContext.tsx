import {
  useEffect,
  useState,
} from 'react'

import {
  getCurrentUser,
  login as loginRequest,
  type CurrentUser,
} from '../services/auth'
import { AuthContext, type AuthProviderProps } from './contextValue'

export function AuthProvider({
  children,
}: AuthProviderProps) {
  const [user, setUser] =
    useState<CurrentUser | null>(null)

  const [loading, setLoading] = useState(() =>
    Boolean(localStorage.getItem('echoguard_token')),
  )

  useEffect(() => {
    const token =
      localStorage.getItem('echoguard_token')

    if (!token) {
      return
    }

    getCurrentUser()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem(
          'echoguard_token',
        )
        setUser(null)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  async function login(
    username: string,
    password: string,
  ) {
    const tokenResponse =
      await loginRequest({
        username,
        password,
      })

    localStorage.setItem(
      'echoguard_token',
      tokenResponse.access_token,
    )

    const currentUser =
      await getCurrentUser()

    setUser(currentUser)
  }

  function logout() {
    localStorage.removeItem(
      'echoguard_token',
    )

    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}