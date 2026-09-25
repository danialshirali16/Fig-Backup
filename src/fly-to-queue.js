// Fly-to-queue feedback: a clone of the row's file tile arcs into the Downloads
// trigger. Vanilla WAAPI, transform/opacity only — no layout animation, no deps.
// A visible tile arcs into the Downloads trigger. The overlay is attached to
// body so the blurred app header cannot clip it. Reduced motion gets a short
// stationary highlight on the destination instead of the traveling tile.
const active = new Set()
let announcer = null
let announceTimer = null
let pendingCount = 0

export function cancelAllFlights() {
  for (const flight of active) flight.cancel()
  active.clear()
}

function announce(text) {
  if (!announcer) {
    announcer = document.createElement('div')
    announcer.setAttribute('role', 'status')
    announcer.setAttribute('aria-live', 'polite')
    announcer.style.cssText = 'position:fixed;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap'
    document.body.appendChild(announcer)
  }
  announcer.textContent = text
}

export function flyToQueue(sourceEl, { describe, trigger, endScale = 0.5 } = {}) {
  const target = trigger || document.querySelector('[data-download-trigger]')
  const icon = target?.querySelector('svg')
  if (!sourceEl || !target) return
  const from = sourceEl.getBoundingClientRect()
  const to = target.getBoundingClientRect()
  if (!from.width || !to.width) return

  if (describe) {
    window.clearTimeout(announceTimer)
    pendingCount += 1
    announceTimer = window.setTimeout(() => {
      announce(describe(pendingCount))
      pendingCount = 0
    }, 150)
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    target.animate(
      [{ boxShadow: '0 0 0 0 transparent' },
        { boxShadow: '0 0 0 4px var(--primary)', offset: 0.5 },
        { boxShadow: '0 0 0 0 transparent' }],
      { duration: 200, easing: 'ease-out' },
    )
    return
  }
  if (active.size >= 3) active.values().next().value?.cancel()

  const ghost = sourceEl.cloneNode(true)
  const wrap = document.createElement('div')
  const size = Math.max(36, Math.min(48, Math.max(from.width, from.height)))
  const startX = from.left + from.width / 2 - size / 2
  const startY = from.top + from.height / 2 - size / 2
  const endX = to.left + to.width / 2 - size / 2
  const endY = to.top + to.height / 2 - size / 2
  wrap.style.cssText = `position:fixed;left:${startX}px;top:${startY}px;width:${size}px;height:${size}px;z-index:60;pointer-events:none;user-select:none;border:1px solid var(--border);border-radius:10px;background:var(--background);box-shadow:0 10px 24px rgb(0 0 0 / 0.25);will-change:transform,opacity`
  wrap.setAttribute('aria-hidden', 'true')
  wrap.setAttribute('data-fly-to-queue', '')
  ghost.style.width = '100%'
  ghost.style.height = '100%'
  ghost.style.padding = '3px'
  ghost.style.objectFit = 'contain'
  wrap.appendChild(ghost)
  document.body.appendChild(wrap)

  const flight = wrap.animate([
    { transform: 'translate(0, 0) scale(1)', opacity: 1 },
    { opacity: 1, offset: 0.7 },
    { transform: `translate(${endX - startX}px, ${endY - startY}px) scale(${endScale})`, opacity: 0.15 },
  ], { duration: 600, easing: 'cubic-bezier(0.3, 0, 0.2, 1)', fill: 'forwards' })

  active.add(flight)
  const settle = () => {
    wrap.remove()
    active.delete(flight)
    // Skip the arrival bump when the manager is open: the new row is the feedback.
    if (target.getAttribute('aria-expanded') !== 'true') {
      icon?.animate(
        [{ transform: 'scale(1)' }, { transform: 'scale(1.25)', offset: 0.5 }, { transform: 'scale(1)' }],
        { duration: 220, easing: 'ease-out' },
      )
    }
  }
  flight.finished.then(settle, () => { wrap.remove(); active.delete(flight) })
}
