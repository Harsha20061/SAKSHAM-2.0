import axios from 'axios'

export function getApiErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (!axios.isAxiosError(error)) {
    return fallback
  }

  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }

  if (detail && typeof detail === 'object' && 'message' in detail) {
    const message = detail.message
    if (typeof message === 'string') {
      return message
    }
  }

  return fallback
}
