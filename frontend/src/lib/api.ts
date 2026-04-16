export async function readErrorMessage(response: Response, fallback: string) {
  const payload = await response.json().catch(() => ({}))
  return payload.detail || payload.message || fallback
}

export async function fetchJson<T>(input: RequestInfo | URL, init: RequestInit, fallback: string): Promise<T> {
  const response = await fetch(input, init)
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, fallback))
  }
  return response.json()
}

export async function expectJson<T>(response: Response, fallback: string): Promise<T> {
  if (!response.ok) {
    throw new Error(await readErrorMessage(response, fallback))
  }
  return response.json()
}
