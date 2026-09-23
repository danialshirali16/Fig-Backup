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
  '20001': [{ key: 'sample-01', name: 'App Screens' }, { key: 'sample-02', name: 'Navigation' }],
  '20002': [{ key: 'sample-03', name: 'Foundations' }, { key: 'sample-04', name: 'UI Kit' }],
  '20003': [{ key: 'sample-05', name: 'Early Concepts' }],
  '20004': [{ key: 'sample-06', name: 'Logo Library' }],
  '20005': [{ key: 'sample-07', name: 'Summer Campaign' }],
  '30001': [{ key: 'sample-08', name: 'Welcome Flow' }],
  '30002': [{ key: 'sample-09', name: 'Profile Settings' }],
  '30003': [{ key: 'sample-10', name: 'Buttons and Inputs' }],
}

const idleStatus = () => ({
  running: false, phase: 'idle', items: [], total: 0, saved: 0,
  existing: 0, skipped: 0, failed: 0, message: '',
  destination: '~/Downloads/Fig Backup', finished: false,
})

export function installPreviewBridge() {
  if (window.pywebview) return

  let preferences = { language: 'en', theme: 'system', onboarding_complete: true }
  const previewTeams = [...teams]
  let status = idleStatus()

  window.pywebview = {
    platform: 'browser-preview',
    api: {
      bootstrap: async () => ({ has_token: true, teams: previewTeams, preferences }),
      discover_teams: async () => ({ teams: previewTeams, auth_required: false }),
      save_preferences: async changes => (preferences = { ...preferences, ...changes }),
      save_token: async () => ({ name: 'Preview user' }),
      open_sign_in: async () => ({ opened: false }),
      folders: async id => ({ folders: foldersByParent[id] || [], legacy: false }),
      subfolders: async id => ({ folders: foldersByParent[id] || [], unavailable: false }),
      files: async id => ({ files: filesByFolder[id] || [], unavailable: false }),
      start_download: async () => {
        status = { ...idleStatus(), phase: 'done', finished: true, total: 1, saved: 1,
          items: [{ status: 'saved' }], message: 'Preview complete' }
        return { started: true }
      },
      stop_download: async () => ({ stopped: true }),
      status: async () => status,
      open_destination: async () => ({ opened: false }),
      open_downloads: async () => ({ opened: false }),
    },
  }
}
