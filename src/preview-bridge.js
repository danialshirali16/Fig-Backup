// Local UI preview only. This bridge is never used by the packaged macOS app.
const previewAvatar = svg => `data:image/svg+xml,${encodeURIComponent(svg)}`
const teams = [
  {
    id: '10001', name: 'Product Design',
    avatar: previewAvatar('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#dbeafe"/><circle cx="32" cy="32" r="19" fill="#2563eb"/><path d="M23 40V24h10a8 8 0 0 1 0 16z" fill="#fff"/></svg>'),
  },
  {
    id: '10002', name: 'Brand Studio',
    avatar: previewAvatar('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#fce7f3"/><path d="M32 10 54 32 32 54 10 32z" fill="#db2777"/><circle cx="32" cy="32" r="10" fill="#fff"/></svg>'),
  },
]

const foldersByParent = {
  '10001': [
    { id: '20001', name: 'Mobile App' },
    { id: '20002', name: 'Design System' },
    { id: '20003', name: 'Explorations' },
  ],
  '10002': [
    { id: '20004', name: 'Brand Assets' },
    { id: '20005', name: 'Campaigns' },
  ],
  '20001': [{ id: '30001', name: 'Onboarding' }, { id: '30002', name: 'Account' }],
  '20002': [{ id: '30003', name: 'Components' }],
}

const filesByFolder = {
  '20001': [{ key: 'sample-01', name: 'App Screens' }, { key: 'sample-02', name: 'Navigation', editorType: 'figjam' }],
  '20002': [{ key: 'sample-03', name: 'Foundations' }, { key: 'sample-04', name: 'UI Kit' }],
  '20003': [{ key: 'sample-05', name: 'Early Concepts', editorType: 'slides' }],
  '20004': [{ key: 'sample-06', name: 'Logo Library' }],
  '20005': [{ key: 'sample-07', name: 'Summer Campaign' }],
  '30001': [{ key: 'sample-08', name: 'Welcome Flow' }],
  '30002': [{ key: 'sample-09', name: 'Profile Settings' }],
  '30003': [{ key: 'sample-10', name: 'Buttons and Inputs' }],
}

const previewTypes = Object.fromEntries(
  Object.values(filesByFolder).flat().map(file => [file.key, file.editorType ?? 'figma']),
)

const idleStatus = () => ({
  running: false, phase: 'idle', items: [], total: 0, saved: 0,
  existing: 0, skipped: 0, failed: 0, message: '',
  destination: '~/Downloads/Fig Backup', finished: false,
})

export function installPreviewBridge() {
  if (window.pywebview) return

  // `?preview=1&browser-install` exercises the one-time setup state.
  // `&fresh` starts with onboarding pending so the setup wizard is shown.
  // `&win-titlebar` fakes the Windows shell to render the in-app caption buttons.
  // `&lang=fa` and `&theme=dark` open in that language / theme, so RTL and dark
  // mode can be checked without clicking through Settings first.
  const params = new URLSearchParams(window.location.search)
  const fakeInstall = params.has('browser-install')
  const fakeWindows = params.has('win-titlebar')
  const slowMode = params.has('slow')
  let failFirstRun = params.has('fail')
  // `&api-error` makes the next folder/file listing fail with a backend-shaped
  // message, so the error banner and its Retry button can be seen. Clicking
  // Retry succeeds, which is the whole point of the affordance.
  const apiErrorMode = params.get('api-error')
  let apiErrorSpent = false
  const maybeApiError = (label, ok) => {
    if (!apiErrorMode || apiErrorSpent) return ok()
    apiErrorSpent = true
    throw new Error({
      network: 'Could not reach Figma: ConnectionError.',
      access: 'Figma refused the request (HTTP 403): Not authorized.',
      rate: 'Figma is busy (HTTP 429).',
    }[apiErrorMode] || 'Something went wrong.')
  }
  let stopRun = null
  const lag = () => new Promise(resolve => window.setTimeout(resolve, slowMode ? 1200 : 0))
  let browserState = fakeInstall ? { phase: 'setting_up', message: '' } : { phase: 'ready', message: '', source: 'chrome' }
  if (fakeInstall) {
    window.setTimeout(() => { browserState = { phase: 'ready', message: '', source: 'chromium' } }, 6000)
  }
  let fakeMaximized = false

  let preferences = {
    language: params.get('lang') || 'en',
    theme: params.get('theme') || 'system',
    onboarding_complete: !params.has('fresh'),
    setup_version: params.has('fresh') ? 0 : 2,
  }
  let browserVerified = false
  let tokenVerified = false
  let signedIn = false
  const previewTeams = [...teams]
  let status = idleStatus()

  window.pywebview = {
    platform: fakeWindows ? 'edgechromium' : 'browser-preview',
    api: {
      bootstrap: async () => ({ has_token: true, teams: previewTeams, preferences, browser: { ...browserState } }),
      discover_teams: async () => lag().then(() => ({ teams: previewTeams, auth_required: false })),
      save_preferences: async changes => (preferences = { ...preferences, ...changes }),
      begin_setup: async () => {
        browserVerified = false
        tokenVerified = false
        preferences = { ...preferences, onboarding_complete: false, setup_version: 0 }
        return { preferences }
      },
      save_token: async () => {
        const setupRequired = preferences.setup_version === 2
        if (setupRequired) {
          browserVerified = false
          preferences = { ...preferences, onboarding_complete: false, setup_version: 0 }
        }
        tokenVerified = !setupRequired
        return { name: 'Preview user', setup_required: setupRequired }
      },
      verify_token: async () => { tokenVerified = true; return { name: 'Preview user' } },
      verify_browser: async () => { browserVerified = true; return { ready: true, source: browserState.source || 'chrome' } },
      open_sign_in: async () => { signedIn = true; return { opened: true } },
      close_sign_in: async () => ({ closed: true }),
      complete_setup: async () => {
        if (!browserVerified || !tokenVerified) throw new Error('Verify browser and token first')
        if (!signedIn) return { completed: false }
        preferences = { ...preferences, onboarding_complete: true, setup_version: 2 }
        return { completed: true, preferences }
      },
      install_browser: async () => ({ started: true }),
      minimize_window: async () => ({ ok: true }),
      toggle_maximize_window: async () => {
        fakeMaximized = !fakeMaximized
        window.dispatchEvent(new Event(fakeMaximized ? 'figbak-window-maximized' : 'figbak-window-restored'))
        return { ok: true }
      },
      close_window: async () => ({ ok: true }),
      begin_resize: async () => ({ ok: false }),
      folders: async id => lag().then(() => maybeApiError('folders', () => ({ folders: foldersByParent[id] || [], legacy: false }))),
      subfolders: async id => lag().then(() => maybeApiError('subfolders', () => ({ folders: foldersByParent[id] || [], unavailable: false }))),
      // The real listing never carries an editor type, so the preview must not
      // either — that is what makes the rows show a placeholder first.
      files: async id => lag().then(() => maybeApiError('files', () => ({
        files: (filesByFolder[id] || []).map(({ editorType, ...rest }) => rest),
        unavailable: false,
      }))),
      // Icons resolve after the names are already on screen; `slow` widens the
      // gap so the placeholder is easy to see.
      file_types: async keys => lag().then(() => Object.fromEntries(
        (keys || []).map(key => [key, previewTypes[key] ?? 'figma']),
      )),
      start_download: async () => {
        // Simulate the real lifecycle: scanning, then per-file checking/opening/preparing/saving.
        const files = ['Home Screen', 'Navigation', 'Profile Settings']
        const sizes = [24.8, 71, 3.2].map(mb => Math.round(mb * 1024 * 1024))
        const run = { running: true, total: files.length, saved: 0, existing: 0, skipped: 0, failed: 0,
          destination: '~/Downloads/Fig Backup/Product Design', finished: false }
        status = { ...run, phase: 'scanning', items: [], message: 'Collecting files…' }
        let tick = 2600
        let stopped = false
        const at = (ms, fn) => window.setTimeout(() => { if (!stopped) fn() }, ms)
        stopRun = () => {
          if (stopped || status.finished) return
          stopped = true
          window.setTimeout(() => {
            status = { ...status, running: false, phase: 'stopped', finished: true, message: 'Stopped after the current file' }
          }, 500)
        }
        const savedUpTo = index => files.map((other, position) => ({
          name: other,
          status: position < index ? 'saved' : position === index ? null : 'queued',
          detail: position < index ? `~/Downloads/Fig Backup/Product Design/${other}.fig` : '',
          size: position < index ? sizes[position] : 0,
        }))
        if (failFirstRun) {
          failFirstRun = false
          at(4400, () => {
            status = { ...status, phase: 'downloading', message: files[1],
              items: savedUpTo(1).map((it, position) => position === 1 ? { ...it, status: 'failed', detail: 'Figma blocked the background editor (HTTP 403)' } : it) }
          })
          at(5600, () => {
            status = { ...status, running: false, phase: 'error', finished: true, failed: 1, message: files[1] }
          })
          return { started: true }
        }
        files.forEach((name, index) => {
          for (const step of ['checking', 'opening', 'preparing', 'saving']) {
            at(tick, () => {
              status = { ...status, phase: 'downloading', message: name,
                items: savedUpTo(index).map((it, position) => position === index ? { ...it, status: step } : it) }
            })
            tick += step === 'opening' ? 1900 : 900
          }
        })
        at(tick + 600, () => {
          status = { ...status, running: false, phase: 'done', finished: true, message: 'Preview complete',
            items: files.map((other, position) => ({
              name: other, status: 'saved',
              detail: `~/Downloads/Fig Backup/Product Design/${other}.fig`,
              size: sizes[position],
            })) }
        })
        return { started: true }
      },
      stop_download: async () => {
        stopRun?.()
        return { stopping: true }
      },
      status: async () => ({ ...status, browser: { ...browserState } }),
      open_destination: async () => ({ opened: false }),
      open_downloads: async () => ({ opened: false }),
      open_path: async () => ({ opened: false }),
    },
  }
}
