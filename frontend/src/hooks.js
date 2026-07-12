import { useEffect, useRef } from 'react'

// Calls `fn` immediately and then every `ms` milliseconds. Uses a ref so the
// latest closure runs without resetting the interval each render.
export function usePolling(fn, ms = 6000) {
  const saved = useRef(fn)
  saved.current = fn
  useEffect(() => {
    let alive = true
    const tick = () => { if (alive) saved.current() }
    tick()
    const id = setInterval(tick, ms)
    return () => { alive = false; clearInterval(id) }
  }, [ms])
}
