import { useEffect, useState } from 'react'

export function useApi(loader, dependencies = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })

  useEffect(() => {
    const controller = new AbortController()
    setState((current) => ({ ...current, error: null, loading: true }))
    loader(controller.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ data: null, error, loading: false })
      })
    return () => controller.abort()
    // Loader identity is deliberately controlled by the caller's dependency list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)

  return state
}
