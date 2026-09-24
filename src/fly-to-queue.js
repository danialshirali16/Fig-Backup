// Fly-to-queue feedback: a clone of the row's file tile arcs into the Downloads
// trigger. Vanilla WAAPI, transform/opacity only — no layout animation, no deps.
// Spec (motion-designer + design-director): 400ms cubic-bezier(0.3,0,0.2,1),
// scale 1→0.5, opacity hold→fade at 0.65, z-60 body append (backdrop-blur trap),
// 1.06×/180ms icon bump on arrival (skipped while the manager is open),
// reduced-motion = 150ms accent tick on the icon + live-region announcement.
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
    icon?.animate(
      [{ backgroundColor: 'color-mix(in oklab, var(--accent) 18%, transparent)' }, { backgroundColor: 'transparent' }],
      { duration: 150, easing: 'ease-out' },
    )
    return
  }
  if (active.size >= 3) active.values().next().value?.cancel()

  const ghost = sourceEl.cloneNode(true)
  const wrap = document.createElement('div')
  wrap.style.cssText = 'position:fixed;left:0;top:0;z-index:60;pointer-events:none;user-select:none'
  wrap.setAttribute('aria-hidden', 'true')
  wrap.appendChild(ghost)
  document.body.appendChild(wrap)

  const endX = to.left + to.width / 2 - from.width / 2
  const endY = to.top + to.height / 2 - from.height / 2
  const flight = wrap.animate([
    { transform: `translate(${from.left}px, ${from.top}px) scale(1)` },
    { transform: `translate(${endX}px, ${endY}px) scale(${endScale})` },
  ], { duration: 400, easing: 'cubic-bezier(0.3, 0, 0.2, 1)', fill: 'forwards' })
  ghost.animate(
    [{ opacity: 1 }, { opacity: 1, offset: 0.65 }, { opacity: 0 }],
    { duration: 400, fill: 'forwards' },
  )

  active.add(flight)
  const settle = () => {
    wrap.remove()
    active.delete(flight)
    // Skip the arrival bump when the manager is open: the new row is the feedback.
    if (target.getAttribute('aria-expanded') !== 'true') {
      icon?.animate(
        [{ transform: 'scale(1)' }, { transform: 'scale(1.06)', offset: 0.5 }, { transform: 'scale(1)' }],
        { duration: 180, easing: 'ease-out' },
      )
    }
  }
  flight.finished.then(settle, () => { wrap.remove(); active.delete(flight) })
}