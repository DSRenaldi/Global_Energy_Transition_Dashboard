const parseError = async (response) => {
  const payload = await response.json().catch(() => ({}))
  return new Error(payload.error ?? `Permintaan gagal (${response.status}).`)
}

export async function getJson(path, signal) {
  const response = await fetch(path, { signal, headers: { Accept: 'application/json' } })
  if (!response.ok) throw await parseError(response)
  return response.json()
}

export const api = {
  overview: (signal) => getJson('/api/overview', signal),
  countries: (signal) => getJson('/api/countries?limit=200', signal),
  fuels: (signal) => getJson('/api/fuels', signal),
  meta: (signal) => getJson('/api/meta', signal),
  momentum: (signal) => getJson('/api/momentum?limit=40', signal),
  risk: (signal) => getJson('/api/risk?limit=100', signal),
  briefing: (signal) => getJson('/api/briefing', signal),
  trends: (entities, signal, start = 2005, end = 2022) =>
    getJson(`/api/trends?entities=${encodeURIComponent(entities.join(','))}&start=${start}&end=${end}`, signal),
}
