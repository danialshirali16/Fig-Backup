import { useEffect, useMemo, useRef, useState } from 'react'
import { Popover as PopoverPrimitive } from 'radix-ui'
import { toast } from 'sonner'
import {
  AlertTriangle, Check, CheckCircle2, ChevronRight, Copy, Download, ExternalLink,
  Folder, FolderInput, Loader2, Minus, Play, RefreshCw, RotateCcw, Settings as SettingsIcon,
  ShieldCheck, Square, X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Toaster } from '@/components/ui/sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { translate, LANGUAGES, RTL_LANGUAGES } from './i18n'
import { downloadFailureDescription } from './download-errors'
import { flyToQueue, cancelAllFlights } from './fly-to-queue'
import iconFileDesign from './assets/figma-file-design.png'
import iconFileSlides from './assets/figma-file-slides.png'
import iconFileFigjam from './assets/figma-file-figjam.png'

const DONE_STATES = ['saved', 'exists', 'renamed']
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))
const firstLine = (text) => String(text || '').split('\n')[0].replace(/^Error:\s*/, '')
const isSigninIssue = (text) => /sign-in|background editor.*403/i.test(String(text || ''))
const isInstallIssue = (text) => /chromium|installation failed/i.test(String(text || ''))

/* Official Figma file-type icons; unknown/legacy editor types read as Design. */
const FILE_ICONS = { figma: iconFileDesign, slides: iconFileSlides, figjam: iconFileFigjam }

/* Per-file export lifecycle captions shown under the running row's name —
   wording is the Figma design's, verbatim. */
const STEP_KEY = { checking: 'stepOpening', opening: 'stepOpening', preparing: 'stepDownloadingAssets', saving: 'stepBundling', retrying: 'stepRetrying' }
const LIVE_FILE_STATES = [...Object.keys(STEP_KEY)]

const fmtBytes = (bytes) => {
  if (!bytes || bytes <= 0) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1 }
  return `${value >= 100 || unit === 0 ? Math.round(value) : value.toFixed(1)} ${units[unit]}`
}

function FileIcon({ editorType, className = 'size-8 shrink-0', ...rest }) {
  return <img src={FILE_ICONS[editorType] ?? iconFileDesign} alt="" aria-hidden="true" draggable="false" className={className} {...rest} />
}

function bridgeReady() {
  if (window.pywebview?.api?.bootstrap) return Promise.resolve(window.pywebview.api)
  return new Promise(resolve => window.addEventListener('pywebviewready', () => resolve(window.pywebview.api), { once: true }))
}

function SetupBar() {
  return (
    <span aria-hidden="true" className="setup-bar-track mt-3 block h-1 overflow-hidden rounded-full bg-muted">
      <span className="setup-bar-fill block h-full rounded-full" />
    </span>
  )
}

/* Skeleton list rows shown while a team/folder listing is being fetched. */
function SkeletonRows({ count = 3, label }) {
  return (
    <div role="status" aria-label={label}>
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="flex items-center gap-3 px-3 py-2.5" aria-hidden="true">
          <span className="size-8 shrink-0 rounded-lg bg-muted motion-safe:animate-pulse" />
          <span className="min-w-0 flex-1 space-y-1.5">
            <span className="block h-3 w-40 max-w-full rounded bg-muted motion-safe:animate-pulse" />
            <span className="block h-2.5 w-24 rounded bg-muted motion-safe:animate-pulse" />
          </span>
        </div>
      ))}
    </div>
  )
}

/* One-time browser setup state. phase: setting_up | failed | ready (ready renders nothing). */
function BrowserSetupState({ phase, message, escalated, tone = 'full', t }) {
  if (phase === 'failed') {
    return (
      <div role="alert" className="flex items-start gap-2.5 rounded-lg border border-[var(--figma-color-border-danger)] bg-[var(--figma-color-bg-danger-tertiary)] px-3.5 py-3">
        <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-semibold text-destructive">{t('setupFailed')}</span>
          {tone === 'full' && message && <span className="mt-0.5 block break-words text-xs leading-snug text-muted-foreground">{message}</span>}
        </span>
      </div>
    )
  }
  return (
    <div role="status" className="rounded-lg border border-primary/25 bg-primary/5 px-3.5 py-3">
      <div className="flex items-start gap-2.5">
        <Loader2 className="mt-0.5 size-4 shrink-0 text-brand-text motion-safe:animate-spin" aria-hidden="true" />
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="min-w-0 break-words text-sm font-semibold">{t('setupHeading')}</span>
            <Badge variant="info">{t('setupBadge')}</Badge>
          </span>
          {tone === 'full' && (
            <span className="mt-0.5 block text-xs leading-relaxed text-muted-foreground text-pretty">{escalated ? t('setupEscalated') : t('setupBody')}</span>
          )}
        </span>
      </div>
      <SetupBar />
    </div>
  )
}

/* Windows frameless titlebar: caption-style controls rendered inside the app header. */
function WindowControls({ maximized, t }) {
  const caption = 'flex h-12 w-12 items-center justify-center text-muted-foreground hover:bg-accent focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-ring'
  return (
    <div className="flex items-center self-stretch">
      <button className={caption} aria-label={t('winMinimize')} title={t('winMinimize')} onClick={() => window.pywebview.api.minimize_window()}>
        <Minus className="size-4" aria-hidden="true" />
      </button>
      <button className={caption} aria-label={maximized ? t('winRestore') : t('winMaximize')} title={maximized ? t('winRestore') : t('winMaximize')} onClick={() => window.pywebview.api.toggle_maximize_window()}>
        {maximized ? <Copy className="size-3.5" aria-hidden="true" /> : <Square className="size-3.5" aria-hidden="true" />}
      </button>
      <button className={caption + ' hover:bg-destructive hover:text-white'} aria-label={t('close')} title={t('close')} onClick={() => window.pywebview.api.close_window()}>
        <X className="size-4" aria-hidden="true" />
      </button>
    </div>
  )
}

/* Invisible edge strips that hand the mouse to the native sizing loop. */
const RESIZE_EDGES = [
  ['inset-x-0 top-0 h-1 cursor-n-resize', 12], ['inset-x-0 bottom-0 h-1 cursor-s-resize', 15],
  ['inset-y-0 left-0 w-1 cursor-w-resize', 10], ['inset-y-0 right-0 w-1 cursor-e-resize', 11],
  ['left-0 top-0 size-2 cursor-nw-resize', 13], ['right-0 top-0 size-2 cursor-ne-resize', 14],
  ['bottom-0 left-0 size-2 cursor-sw-resize', 16], ['bottom-0 right-0 size-2 cursor-se-resize', 17],
]

function TeamAvatar({ team, className = 'size-8' }) {
  const [failed, setFailed] = useState(false)
  useEffect(() => setFailed(false), [team.avatar])
  const avatar = typeof team.avatar === 'string' && team.avatar.startsWith('data:image/') ? team.avatar : ''
  return (
    <span className={`flex ${className} shrink-0 items-center justify-center overflow-hidden rounded-lg bg-primary/10 text-sm font-bold text-brand-text`} aria-hidden="true">
      {avatar && !failed
        ? <img src={avatar} alt="" className="size-full object-cover" onError={() => setFailed(true)} />
        : team.name.slice(0, 1).toUpperCase()}
    </span>
  )
}

function App() {
  const [api, setApi] = useState(null)
  const [ready, setReady] = useState(false)
  const [hasToken, setHasToken] = useState(false)
  const [preferences, setPreferences] = useState({ language: 'en', theme: 'system', onboarding_complete: false })
  const [systemDark, setSystemDark] = useState(window.matchMedia('(prefers-color-scheme: dark)').matches)
  const [view, setView] = useState('wizard') // wizard | teams | browse | settings
  const [settingsReturn, setSettingsReturn] = useState('teams')
  const [wizardStep, setWizardStep] = useState('token') // token | signin
  const [verifiedName, setVerifiedName] = useState('')
  const [token, setToken] = useState('')
  const [tokenError, setTokenError] = useState('')
  const [teams, setTeams] = useState([])
  const [team, setTeam] = useState(null)
  const [folders, setFolders] = useState([])
  const [folder, setFolder] = useState(null)
  const [trail, setTrail] = useState([])
  const [files, setFiles] = useState([])
  const [authRequired, setAuthRequired] = useState(false)
  const [loginOpen, setLoginOpen] = useState(false)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [progress, setProgress] = useState({ running: false, phase: 'idle', items: [], total: 0, saved: 0, existing: 0, skipped: 0, failed: 0, message: '', destination: '', finished: false })
  const [selectMode, setSelectMode] = useState(false)
  const [selection, setSelection] = useState({}) // teamId -> { folders: [], files: [] }
  const [queue, setQueue] = useState([])
  const [queueOpen, setQueueOpen] = useState(false)
  const [browserSetup, setBrowserSetup] = useState({ phase: 'ready', message: '' })
  const [setupReadyFlash, setSetupReadyFlash] = useState(false)
  const [now, setNow] = useState(Date.now())
  const queueRef = useRef([])
  const queueRunnerRef = useRef(false)
  const stopAfterCurrentRef = useRef(false)
  const selectBtnRef = useRef(null)
  const runIdRef = useRef(0)
  const browserWatchRef = useRef(false)
  const setupStartRef = useRef(0)
  const prevSetupPhaseRef = useRef('ready')
  const scanStartRef = useRef(0)
  const language = preferences.language
  const t = (key, values) => translate(language, key, values)
  const countCopy = (key, count) => t(count === 1 ? `${key}One` : key, { count })
  const appearance = preferences.theme === 'system' ? (systemDark ? 'dark' : 'light') : preferences.theme
  const rtl = RTL_LANGUAGES.has(language)
  const languageNative = LANGUAGES.find(item => item.code === language)?.native || language
  const [sortedFolders, sortedFiles] = useMemo(() => {
    const collator = new Intl.Collator(language, { sensitivity: 'base', numeric: true })
    const byName = (a, b) => collator.compare(a.name || '', b.name || '')
    return [[...folders].sort(byName), [...files].sort(byName)]
  }, [folders, files, language])
  const nativeMac = api && window.pywebview?.platform === 'cocoa'
  const nativeWin = api && window.pywebview?.platform === 'edgechromium'
  const [maximized, setMaximized] = useState(false)

  useEffect(() => {
    if (!nativeWin) return
    const onMax = () => setMaximized(true)
    const onRestore = () => setMaximized(false)
    window.addEventListener('figbak-window-maximized', onMax)
    window.addEventListener('figbak-window-restored', onRestore)
    return () => {
      window.removeEventListener('figbak-window-maximized', onMax)
      window.removeEventListener('figbak-window-restored', onRestore)
    }
  }, [nativeWin])

  const setupPending = browserSetup.phase === 'setting_up'
  const setupFailed = browserSetup.phase === 'failed'
  const setupBlocked = setupPending || setupFailed
  const setupEscalated = setupPending && now - setupStartRef.current > 300000

  const teamSel = team ? (selection[team.id] || { folders: [], files: [] }) : { folders: [], files: [] }
  const selCount = teamSel.folders.length + teamSel.files.length

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setSystemDark(media.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => {
    const root = document.documentElement
    root.lang = language
    root.dir = rtl ? 'rtl' : 'ltr'
    root.classList.toggle('dark', appearance === 'dark')
  }, [language, appearance])

  useEffect(() => {
    bridgeReady().then(async bridge => {
      setApi(bridge)
      try {
        const initial = await bridge.bootstrap()
        setHasToken(initial.has_token)
        setPreferences(initial.preferences)
        setTeams(initial.teams || [])
        if (initial.browser) setBrowserSetup(initial.browser)
        if (initial.browser && initial.browser.phase !== 'ready') watchBrowser(bridge)
        if (initial.preferences.onboarding_complete && initial.has_token) {
          setView('teams')
          await discover(bridge)
        } else {
          setView('wizard')
          setWizardStep(initial.has_token ? 'signin' : 'token')
        }
        setReady(true)
      } catch (err) {
        setError(firstLine(err))
        setReady(true)
      }
    })
  }, [])

  /* Flying tiles target the header trigger, which only exists in app views. */
  useEffect(() => { cancelAllFlights() }, [view])

  /* Esc closes the popover through Radix, or exits select mode. */
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return
      if (!queueOpen && selectMode) { setSelectMode(false); selectBtnRef.current?.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [queueOpen, selectMode])

  /* One-time setup: tick so the 5-minute escalation copy can swap in. */
  useEffect(() => {
    if (browserSetup.phase !== 'setting_up') return
    const timer = window.setInterval(() => setNow(Date.now()), 15000)
    return () => window.clearInterval(timer)
  }, [browserSetup.phase])

  async function call(label, action) {
    setBusy(label); setError(''); toast.dismiss('app-notice')
    try { return await action() }
    catch (err) { setError(firstLine(err)); return null }
    finally { setBusy('') }
  }

  async function savePrefs(changes) {
    const result = await call('preferences', () => api.save_preferences(changes))
    if (result) setPreferences(result)
    return result
  }

  async function discover(bridge = api) {
    const result = await call('teams', () => bridge.discover_teams())
    if (!result) return
    setTeams(result.teams || [])
    setAuthRequired(!!result.auth_required)
  }

  /* One-time browser setup: poll the bridge until the installer settles. */
  async function watchBrowser(bridge = api) {
    if (browserWatchRef.current || !bridge) return
    browserWatchRef.current = true
    setupStartRef.current = Date.now()
    try {
      for (;;) {
        const s = await bridge.status()
        const next = s.browser || { phase: 'ready', message: '' }
        setBrowserSetup(next)
        if (next.phase === 'ready' && prevSetupPhaseRef.current !== 'ready') {
          toast.success(t('setupReady'), { id: 'app-notice' })
          setSetupReadyFlash(true)
          window.setTimeout(() => setSetupReadyFlash(false), 2500)
        }
        prevSetupPhaseRef.current = next.phase
        if (next.phase !== 'setting_up') break
        await sleep(500)
      }
    } catch { /* bridge unavailable during shutdown */ }
    finally { browserWatchRef.current = false }
  }

  async function retryBrowserSetup() {
    await call('browser-setup', () => api.install_browser())
    watchBrowser()
  }

  async function saveTokenContinue(event) {
    event?.preventDefault()
    if (!token.trim()) {
      setTokenError(t('tokenRequired'))
      document.getElementById(view === 'settings' ? 'token-settings' : 'token-wizard')?.focus()
      return
    }
    setTokenError('')
    const result = await call('token', () => api.save_token(token))
    if (!result) return
    setHasToken(true)
    setToken('')
    if (view === 'settings') {
      toast.success(t('tokenSavedNotice'), { id: 'app-notice' })
      if (settingsReturn === 'wizard') setWizardStep('signin')
      return
    }
    setVerifiedName(result.name || 'Figma')
    setWizardStep('signin')
  }

  async function completeSetup() {
    const ok = await savePrefs({ onboarding_complete: true })
    if (!ok) return
    setView('teams')
    await discover()
  }

  async function signInNow() {
    if (!loginOpen) {
      const result = await call('sign-in', () => api.open_sign_in())
      if (result) setLoginOpen(true)
      return
    }
    await completeSetup()
  }

  function openWizard(step) {
    setWizardStep(step)
    setView('wizard')
  }

  async function chooseTeam(value) {
    setTeam(value); setView('browse'); setFolder(null); setTrail([]); setFolders([]); setFiles([]); setSelectMode(false)
    const result = await call('folders', () => api.folders(value.id))
    if (!result) return
    setFolders(result.folders || [])
    if (result.legacy) toast.warning(t('legacyNotice'), { id: 'app-notice', duration: Infinity })
  }

  async function browseFolder(value, path = [...trail, value]) {
    setFolder(value); setTrail(path); setFolders([]); setFiles([])
    const result = await call('browse', async () => {
      const children = await api.subfolders(value.id)
      const fileResult = await api.files(value.id)
      return { children, fileResult }
    })
    if (!result) return
    setFolders(result.children.folders || [])
    setFiles(result.fileResult.files || [])
    if (result.children.unavailable || result.fileResult.unavailable) toast.warning(t('folderRestricted'), { id: 'app-notice', duration: Infinity })
  }

  async function backTo(index) {
    if (index < 0) { await chooseTeam(team); return }
    await browseFolder(trail[index], trail.slice(0, index + 1))
  }

  /* ---------- hierarchical per-team selection ---------- */
  function updateSelection(mutator) {
    if (!team) return
    setSelection(prev => {
      const cur = prev[team.id] || { folders: [], files: [] }
      return { ...prev, [team.id]: mutator(cur) }
    })
  }
  const folderSelected = (id) => teamSel.folders.some(f => f.id === id)
  const fileSelected = (key) => teamSel.files.some(f => f.key === key)
  function toggleFolder(f) {
    updateSelection(cur => ({
      ...cur,
      folders: folderSelected(f.id) ? cur.folders.filter(x => x.id !== f.id) : [...cur.folders, f],
    }))
  }
  function toggleFile(f) {
    updateSelection(cur => ({
      ...cur,
      files: fileSelected(f.key) ? cur.files.filter(x => x.key !== f.key) : [...cur.files, { key: f.key, name: f.name, folder, editorType: f.editorType }],
    }))
  }
  const visibleAllSelected = (folders.length + files.length > 0) && folders.every(f => folderSelected(f.id)) && files.every(f => fileSelected(f.key))
  const visibleSomeSelected = folders.some(f => folderSelected(f.id)) || files.some(f => fileSelected(f.key))
  const allState = visibleAllSelected ? 'on' : visibleSomeSelected ? 'half' : 'off'
  function onSelectAll() {
    if (visibleAllSelected) {
      updateSelection(cur => ({
        folders: cur.folders.filter(f => !folders.some(v => v.id === f.id)),
        files: cur.files.filter(f => !files.some(v => v.key === f.key)),
      }))
    } else {
      updateSelection(cur => ({
        folders: [...cur.folders.filter(f => !folders.some(v => v.id === f.id)), ...folders],
        files: [...cur.files.filter(f => !files.some(v => v.key === f.key)), ...files.map(f => ({ key: f.key, name: f.name, folder }))],
      }))
    }
  }
  function clearSelection() { updateSelection(() => ({ folders: [], files: [] })) }
  function exitSelectMode() { setSelectMode(false); selectBtnRef.current?.focus() }

  /* ---------- sequential backup queue ---------- */
  function changeQueue(update) {
    const next = update(queueRef.current)
    queueRef.current = next
    setQueue(next)
  }
  function updateQueueItem(id, patch) {
    changeQueue(q => q.map(it => (it.id === id ? { ...it, ...patch } : it)))
  }
  async function waitForRunEnd(runId) {
    for (;;) {
      if (runIdRef.current !== runId) return { cancelled: true }
      const s = await api.status()
      setProgress(s)
      if (!s.running && s.finished) return s
      await sleep(400)
    }
  }
  function routeToSignin() {
    setQueueOpen(false)
    openWizard('signin')
  }
  async function runQueue() {
    if (queueRunnerRef.current) return
    queueRunnerRef.current = true
    const runId = ++runIdRef.current
    try {
      for (;;) {
        const item = queueRef.current.find(it => it.status === 'queued')
        if (!item || runIdRef.current !== runId) break
        updateQueueItem(item.id, { status: 'running', detail: '' })
        try {
          const sel = item.kind === 'team'
            ? { scope: 'team' }
            : item.kind === 'folder'
              ? { scope: 'folder', folder: item.folder }
              : { scope: 'file', folder: item.folder, file_key: item.file_key }
          scanStartRef.current = Date.now()
          await api.start_download({ team: item.team, ...sel })
          const s = await waitForRunEnd(runId)
          if (s.cancelled) break
          if (s.warning) toast.warning(backendWarning(s.warning), { id: 'app-notice', duration: Infinity })
          if (s.phase === 'attention' || isSigninIssue(s.message)) {
            updateQueueItem(item.id, { status: 'failed', detail: t('interrupted') })
            routeToSignin()
            break
          }
          // Caption data for the finished rows: total bytes and the on-disk path.
          const doneFiles = s.items.filter(i => DONE_STATES.includes(i.status))
          const runPath = item.kind === 'file' ? (doneFiles[0]?.detail || '') : (s.destination || '')
          updateQueueItem(item.id, {
            status: s.phase === 'stopped' ? 'stopped' : s.phase === 'error' || s.failed > 0 ? 'failed' : 'done',
            detail: s.phase === 'error' || s.failed > 0 ? downloadFailureDescription(s, item.name, t) : '',
            bytes: doneFiles.reduce((sum, i) => sum + (i.size || 0), 0),
            filesDone: doneFiles.length,
            runPath,
          })
        } catch (err) {
          const msg = firstLine(err)
          if (isSigninIssue(msg)) {
            updateQueueItem(item.id, { status: 'failed', detail: t('interrupted') })
            routeToSignin()
            break
          }
          updateQueueItem(item.id, { status: 'failed', detail: isInstallIssue(msg) ? t('queueBlockedDetail') : (msg || t('downloadFailureFallback')) })
        }
        if (stopAfterCurrentRef.current) break
      }
    } finally {
      queueRunnerRef.current = false
      stopAfterCurrentRef.current = false
    }
  }
  function enqueueItems(items, showDetails = true) {
    changeQueue(current => queueRunnerRef.current ? [...current, ...items] : items)
    if (showDetails) setQueueOpen(true)
    void runQueue()
  }
  function startSelectionBackup() {
    if (!team || selCount === 0) return
    const batch = Date.now()
    const items = [
      ...teamSel.folders.map((f, i) => ({ id: `f-${batch}-${i}`, kind: 'folder', name: f.name, team, folder: f, status: 'queued', detail: '' })),
      ...teamSel.files.map((f, i) => ({ id: `k-${batch}-${i}`, kind: 'file', name: f.name, team, folder: f.folder, file_key: f.key, editorType: f.editorType, status: 'queued', detail: '' })),
    ]
    clearSelection()
    enqueueItems(items)
  }
  function retryItem(id) {
    updateQueueItem(id, { status: 'queued', detail: '' })
    void runQueue()
  }
  function cancelItem(id) {
    const item = queueRef.current.find(it => it.id === id)
    if (!item) return
    if (item.status === 'running') { void stopCurrent(); return }
    if (item.status !== 'done') changeQueue(q => q.filter(it => it.id !== id))
  }
  function continueItemNext(id) {
    changeQueue(q => {
      const item = q.find(it => it.id === id)
      if (!item || item.status !== 'queued') return q
      const rest = q.filter(it => it.id !== id)
      const insertAt = rest.findIndex(it => it.status === 'queued')
      if (insertAt === -1) return [...rest, item]
      return [...rest.slice(0, insertAt), item, ...rest.slice(insertAt)]
    })
    void runQueue()
  }
  function clearFinished() {
    changeQueue(q => q.filter(it => !['done', 'stopped', 'failed'].includes(it.status)))
  }
  async function stopCurrent() {
    stopAfterCurrentRef.current = true
    try { await api.stop_download() } catch { /* noop */ }
  }

  function openSettings() { setSettingsReturn(view === 'settings' ? 'teams' : view); setQueueOpen(false); setView('settings'); setError(''); toast.dismiss('app-notice') }
  function leaveSettings() { setView(settingsReturn || 'teams'); setToken(''); setTokenError(''); setError(''); toast.dismiss('app-notice') }
  function redoSetup() { setVerifiedName(''); setView('wizard'); setWizardStep(hasToken ? 'signin' : 'token') }

  function startDownload(sel) {
    if (!team || !sel) return
    enqueueItems([{
      id: 'run-' + Date.now(),
      kind: sel.scope,
      name: sel.name || sel.folder?.name || team.name,
      team,
      folder: sel.folder,
      file_key: sel.file_key,
      editorType: sel.editor_type,
      status: 'queued', detail: '',
    }], false)
  }

  const doneCount = progress.items.filter(item => DONE_STATES.includes(item.status)).length
  const loadingBrowse = busy === 'browse' || busy === 'folders'
  const activeWork = queue.some(item => item.status === 'running' || item.status === 'queued')
  const queueDoneCount = queue.filter(item => item.status === 'done').length
  const downloadPct = queue.length ? Math.round(queueDoneCount / queue.length * 100) : 0
  /* Live per-file stage for the running row's caption; re-renders come from the 400 ms polls. */
  const liveFile = progress.running && progress.phase === 'downloading'
    ? progress.items.find(item => LIVE_FILE_STATES.includes(item.status)) : null
  const scanning = progress.running && progress.phase === 'scanning'
  const scanSeconds = scanning && scanStartRef.current ? Math.max(0, Math.floor((Date.now() - scanStartRef.current) / 1000)) : 0
  const scanLabel = scanSeconds ? `${Math.floor(scanSeconds / 60)}:${String(scanSeconds % 60).padStart(2, '0')}` : ''
  const runningRows = queue.filter(item => item.status !== 'done')
  const completedRows = queue.filter(item => item.status === 'done')
  const clearable = completedRows.length > 0

  const Spinner = () => <Loader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />

  function backendWarning(w) {
    const match = /subfolders for (\d+) folder/.exec(String(w || ''))
    return match ? t('subfolderWarning', { count: match[1] }) : w
  }
  function errorHelp(message) {
    if (/token|HTTP 401/i.test(message)) return t('tokenRecovery')
    if (/HTTP 403|permission|access denied/i.test(message)) return t('accessRecovery')
    if (/HTTP 429/i.test(message)) return t('rateRecovery')
    if (/valid team|cannot be empty|Choose a/i.test(message)) return ''
    return t('errorPrefix')
  }

  /* ---------- wizard ---------- */
  const wizard = view === 'wizard' && (
    <Card className="mx-auto w-full max-w-xl p-0 ring-0">
      <div className="mb-5 flex items-center">
        {[['token', t('stepToken')], ['signin', t('stepSignin')]].map(([key, label], i) => {
          const cur = wizardStep === key
          const done = key === 'token' && wizardStep === 'signin'
          return (
            <div key={key} className="relative flex flex-1 flex-col items-center gap-1.5">
              {i > 0 && <span aria-hidden="true" className={'absolute top-3 h-0.5 start-[calc(-50%+22px)] end-[calc(50%+22px)] ' + (done || cur ? 'bg-primary' : 'bg-muted')} />}
              <span className={'relative z-10 grid size-7 place-items-center rounded-full text-[11px] font-extrabold ' + (
                cur ? 'bg-primary/10 text-brand-text ring-2 ring-primary/25' : done ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
              )}>
                {done ? <Check className="size-3.5" /> : i + 1}
              </span>
              <span className={'text-[11px] font-bold ' + (cur ? 'text-foreground' : 'text-muted-foreground')}>{label}</span>
            </div>
          )
        })}
      </div>
      {wizardStep === 'token' ? (
        <>
          <div className="mb-4 text-center">
            <h1 className="text-xl font-bold tracking-tight text-balance">{t('tokenTitle')}</h1>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground text-pretty">{t('stepOf', { step: 1, total: 2 })} — {t('tokenDescription')}</p>
          </div>
          <form onSubmit={saveTokenContinue} className="grid gap-3">
            <Label htmlFor="token-wizard">{t('tokenLabel')}</Label>
            <Input id="token-wizard" type="password" value={token} onInput={e => { setToken(e.currentTarget.value); setTokenError('') }} placeholder="figd_…" autoComplete="off" aria-invalid={!!tokenError} />
            {tokenError && <p role="alert" className="text-xs font-medium text-destructive">{tokenError}</p>}
            <p className="text-xs text-muted-foreground">{t('tokenHint')}</p>
            <Alert className="text-start">
              <ShieldCheck />
              <AlertDescription className="text-xs leading-relaxed">{t('tokenPrivacy')}</AlertDescription>
            </Alert>
            {setupPending && <BrowserSetupState phase="setting_up" tone="slim" t={t} />}
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <span className="me-auto text-[11px] text-muted-foreground">
                {t('language')}: <b className="font-semibold text-foreground">{languageNative}</b> · <button type="button" className="font-semibold text-brand-text hover:underline" onClick={openSettings}>{t('settings')}</button>
              </span>
              <Button type="submit" disabled={!!busy}>{busy === 'token' ? <Spinner /> : null} {t('saveContinue')}</Button>
            </div>
          </form>
        </>
      ) : (
        <>
          <div className="mb-4 text-center">
            <h1 className="text-xl font-bold tracking-tight text-balance">{t('signInTitle')}</h1>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground text-pretty">{t('stepOf', { step: 2, total: 2 })} — {t('signinCopy')}</p>
          </div>
          <div className="grid gap-3">
            {verifiedName && (
              <div className="flex items-center justify-between rounded-lg border border-success/30 bg-success/10 px-3.5 py-2.5 text-sm">
                <span className="font-medium text-success">{t('verifiedAs', { name: verifiedName })}</span>
                <Badge variant="success"><CheckCircle2 className="size-3" /> {t('verified')}</Badge>
              </div>
            )}
            <Alert className="text-start">
              <ShieldCheck />
              <AlertDescription className="leading-relaxed">{t('signInDescription')}</AlertDescription>
            </Alert>
            {setupBlocked && (
              <BrowserSetupState phase={setupFailed ? 'failed' : 'setting_up'} message={browserSetup.message} escalated={setupEscalated} t={t} />
            )}
            <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
              <Button variant="ghost" onClick={completeSetup}>{t('signinLater')}</Button>
              {setupPending ? (
                <Button disabled><Spinner /> {t('setupWaiting')}</Button>
              ) : setupFailed ? (
                <Button onClick={retryBrowserSetup} disabled={!!busy}>
                  {busy === 'browser-setup' ? <Spinner /> : <RotateCcw className="size-4" />} {t('setupRetry')}
                </Button>
              ) : (
                <Button onClick={signInNow} disabled={!!busy}>
                  {busy === 'sign-in' ? <Spinner /> : loginOpen ? <CheckCircle2 className="size-4" /> : <ExternalLink className="size-4" />}
                  {loginOpen ? t('iveSignedIn') : t('openSignIn')}
                </Button>
              )}
            </div>
          </div>
        </>
      )}
    </Card>
  )

  /* ---------- download manager popover ---------- */
  const rowBtn = 'grid size-7 flex-none place-items-center rounded-md text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring'
  const rowCaption = (item) => {
    if (item.status === 'queued') return <span>{t('captionQueue')}</span>
    if (item.status === 'running') {
      if (stopAfterCurrentRef.current) return <span>{t('stopping')}</span>
      if (scanning) {
        return <span>{t('collectingFiles')}{scanLabel && <span aria-hidden="true" className="tabular-nums"> · {scanLabel}</span>}</span>
      }
      if (liveFile) {
        const count = item.kind !== 'file' && progress.total > 0
          ? <> · {t(progress.total === 1 ? 'progressCountOne' : 'progressCount', { done: doneCount, total: progress.total })}</>
          : null
        return <span>{t(STEP_KEY[liveFile.status])}{count}</span>
      }
      return <span>{setupPending ? t('setupWaiting') : t('running')}</span>
    }
    if (item.status === 'stopped') return <span>{item.detail || t('statusStopped')}</span>
    if (item.status === 'failed') return <span className="text-destructive">{item.detail || t('statusFailed')}</span>
    if (item.kind === 'file') return <span>{fmtBytes(item.bytes) || t('statusSaved')}</span>
    return <span>{countCopy('filesCount', item.filesDone || 0)}</span>
  }
  const rowActions = (item) => {
    if (item.status === 'running') {
      return (
        <span className="relative flex size-7 flex-none items-center justify-center">
          <Loader2 className="size-3.5 text-muted-foreground motion-safe:animate-spin group-hover:opacity-0" aria-hidden="true" />
          <button type="button" onClick={() => cancelItem(item.id)} aria-label={t('cancelItem')} title={t('cancelItem')}
            className="absolute inset-0 hidden place-items-center rounded-md text-muted-foreground transition-colors duration-150 hover:bg-accent hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring group-hover:grid group-focus-within:grid">
            <X className="size-3.5" aria-hidden="true" />
          </button>
        </span>
      )
    }
    if (item.status === 'queued') {
      return (
        <span className="hidden flex-none items-center gap-0.5 group-hover:flex group-focus-within:flex">
          <button type="button" onClick={() => cancelItem(item.id)} aria-label={t('cancelItem')} title={t('cancelItem')} className={rowBtn}>
            <X className="size-3.5" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => continueItemNext(item.id)} aria-label={t('continueNow')} title={t('continueNow')} className={rowBtn}>
            <Play className="size-3.5" aria-hidden="true" />
          </button>
        </span>
      )
    }
    if (item.status === 'done' && item.runPath) {
      return (
        <button type="button" onClick={() => api.open_path(item.runPath)} aria-label={t('showInFolder')} title={t('showInFolder')} className={rowBtn + ' hidden group-hover:grid group-focus-within:grid'}>
          <FolderInput className="size-3.5" aria-hidden="true" />
        </button>
      )
    }
    if (item.status === 'failed' || item.status === 'stopped') {
      return (
        <span className="flex flex-none items-center gap-0.5">
          <button type="button" onClick={() => cancelItem(item.id)} aria-label={t('cancelItem')} title={t('cancelItem')} className={rowBtn}>
            <X className="size-3.5" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => retryItem(item.id)} aria-label={t('retry')} title={t('retry')} className={rowBtn}>
            <RefreshCw className="size-3.5" aria-hidden="true" />
          </button>
        </span>
      )
    }
    return null
  }
  const downloadRow = (item) => (
    <div key={item.id} className="group mx-2 flex min-h-11 items-center gap-3 rounded-[6px] px-2 transition-colors duration-150 hover:bg-muted">
      {item.kind === 'file'
        ? <FileIcon editorType={item.editorType} className="size-7 shrink-0" />
        : item.kind === 'folder'
          ? (
            <span aria-hidden="true" className="grid size-7 flex-none place-items-center rounded-md bg-muted text-muted-foreground">
              <Folder className="size-4" />
            </span>
          )
          : <TeamAvatar team={item.team} className="size-7 shrink-0" />}
      <span className="min-w-0 flex-1">
        <span className="block break-words text-xs font-medium leading-4 [overflow-wrap:anywhere]"><bdi>{item.name}</bdi></span>
        <span dir="auto" className="mt-1 block break-words text-xs leading-4 text-muted-foreground [overflow-wrap:anywhere]">{rowCaption(item)}</span>
      </span>
      {rowActions(item)}
    </div>
  )
  const downloadManager = (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex shrink-0 items-center gap-1.5 ps-4 pe-2 py-1.5">
        <h2 className="min-w-0 flex-1 text-sm font-semibold">{t('downloadManagerTitle')}</h2>
        {clearable && (
          <Button variant="ghost" size="sm" onClick={clearFinished} title={t('clearFinishedTitle')}>
            {t('clearFinished')}
          </Button>
        )}
        <button type="button" aria-label={t('close')} onClick={() => setQueueOpen(false)} className="grid size-8 flex-none place-items-center rounded-md text-muted-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring">
          <X className="size-4" aria-hidden="true" />
        </button>
      </div>
      {setupReadyFlash && (
        <div role="status" className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-success">
          <CheckCircle2 className="size-3.5" aria-hidden="true" /> {t('setupReady')}
        </div>
      )}
      {setupPending && (
        <div className="px-4 py-2">
          <BrowserSetupState phase="setting_up" tone="slim" t={t} />
        </div>
      )}
      {setupFailed && (
        <div className="px-4 py-2">
          <BrowserSetupState phase="failed" message={browserSetup.message} t={t} />
          <Button variant="outline" size="sm" onClick={retryBrowserSetup} className="mt-2 w-full">
            {busy === 'browser-setup' ? <Spinner /> : <RotateCcw className="size-3" />} {t('setupRetry')}
          </Button>
        </div>
      )}
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {runningRows.length > 0 && (
          <section>
            <div className="flex items-center justify-between border-y border-border bg-muted px-4 py-1.5">
              <h3 className="text-xs font-medium text-muted-foreground">{t('sectionInProgress')}</h3>
              <span aria-hidden="true" className="text-xs tabular-nums text-muted-foreground">{runningRows.length}</span>
            </div>
            <div className="py-1">{runningRows.map(downloadRow)}</div>
          </section>
        )}
        {completedRows.length > 0 && (
          <section>
            <div className="flex items-center justify-between border-y border-border bg-muted px-4 py-1.5">
              <h3 className="text-xs font-medium text-muted-foreground">{t('sectionCompleted')}</h3>
              <span aria-hidden="true" className="text-xs tabular-nums text-muted-foreground">{completedRows.length}</span>
            </div>
            <div className="py-1">{completedRows.map(downloadRow)}</div>
          </section>
        )}
        {!queue.length && (
          <div className="flex flex-1 flex-col items-center justify-center px-4 text-center text-sm text-muted-foreground">
            <Download className="mb-2 size-5 opacity-60" aria-hidden="true" />
            {t('downloadManagerEmpty')}
          </div>
        )}
      </div>
    </div>
  )

  const inSelect = view === 'browse' && selectMode

  return (
    <div className={'flex min-h-screen flex-col' + (nativeMac ? ' native-mac-titlebar' : '') + (nativeWin ? ' native-win-titlebar' : '')}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:shadow">{t('skipToContent')}</a>
      <Toaster theme={appearance} position={rtl ? 'bottom-left' : 'bottom-right'} closeButton offset={16} />

      <header
        className="pywebview-drag-region sticky top-0 z-30 border-b bg-background/80 backdrop-blur relative"
        onDoubleClick={nativeWin ? () => window.pywebview.api.toggle_maximize_window() : undefined}
      >
        {nativeWin && (
          <div className="absolute inset-y-0 end-0 z-10">
            <WindowControls maximized={maximized} t={t} />
          </div>
        )}
        <div className="pywebview-drag-region app-header-inner mx-auto flex h-12 w-full max-w-[680px] items-center gap-2.5 ps-4 pe-2">
          {view === 'settings' ? (
            <div className="flex min-w-0 items-center gap-1">
              <Button variant="ghost" size="icon-lg" aria-label={t('back')} title={t('back')} onClick={leaveSettings}>
                <ChevronRight className="size-4 rotate-180 rtl:rotate-0" aria-hidden="true" />
              </Button>
              <span className="text-lg font-semibold tracking-tight">{t('settingsTitle')}</span>
            </div>
          ) : <span className="text-sm font-medium tracking-tight">Fig Backup</span>}
          <div className="ms-auto flex items-center gap-1">
            {view !== 'wizard' && view !== 'settings' && (
              <PopoverPrimitive.Root open={queueOpen} onOpenChange={setQueueOpen}>
                <PopoverPrimitive.Trigger asChild>
                  <Button variant="ghost" size="icon" data-download-trigger="" aria-label={t('downloadManagerTitle')} title={t('downloadManagerTitle')} aria-expanded={queueOpen} aria-controls="download-manager" className="relative">
                    <Download className="size-4" aria-hidden="true" />
                    {activeWork && (
                      <span aria-hidden="true" className="dl-progress absolute inset-x-1 bottom-px h-[3px] overflow-hidden rounded-full bg-muted">
                        <span className="block h-full rounded-full bg-primary transition-[width] duration-300" style={{ width: `${downloadPct}%` }} />
                      </span>
                    )}
                  </Button>
                </PopoverPrimitive.Trigger>
                <PopoverPrimitive.Portal>
                  <PopoverPrimitive.Content id="download-manager" aria-label={t('downloadManagerTitle')} side="bottom" align="end" sideOffset={8} collisionPadding={8} onOpenAutoFocus={event => event.preventDefault()} className="z-50 flex max-h-[min(800px,var(--radix-popover-content-available-height))] min-h-[400px] w-[min(375px,calc(100vw-24px))] flex-col overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-xl outline-none">
                    {downloadManager}
                  </PopoverPrimitive.Content>
                </PopoverPrimitive.Portal>
              </PopoverPrimitive.Root>
            )}
            {view !== 'wizard' && view !== 'settings' && (
              <Button variant="ghost" size="icon" aria-label={t('settings')} title={t('settings')} onClick={openSettings}>
                <SettingsIcon className="size-4" aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>
      </header>

      <main id="main" className={'mx-auto w-full max-w-[680px] flex-1 ' + (view === 'wizard' ? 'px-4 pt-7 pb-10' : 'px-2 pt-4 pb-8')}>
        {error && (
          <div role="alert" className="mb-4 flex items-start gap-2.5 rounded-lg border border-[var(--figma-color-border-danger)] bg-[var(--figma-color-bg-danger-tertiary)] px-3.5 py-2.5 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span className="min-w-0 flex-1 break-words">{error} {errorHelp(error)}</span>
            <button onClick={() => setError('')} aria-label={t('close')} className="grid size-8 shrink-0 place-items-center rounded-md hover:bg-destructive/15 focus-visible:outline-2 focus-visible:outline-ring"><X className="size-3.5" /></button>
          </div>
        )}
        {!ready ? (
          <div role="status" className="flex items-center justify-center gap-2.5 py-24 text-muted-foreground"><Spinner /> {t('loading')}</div>
        ) : view === 'wizard' ? wizard : <>
          {view !== 'settings' && <div className="mb-5">
            <div className="flex flex-wrap items-center justify-between gap-2.5 px-3">
              {view === 'browse' ? (
                <div className="flex min-w-0 items-center gap-2">
                  <Button variant="ghost" size="icon-sm" aria-label={t('back')} onClick={() => (trail.length > 1 ? backTo(trail.length - 2) : trail.length ? backTo(-1) : setView('teams'))}>
                    <ChevronRight className="rotate-180 rtl:rotate-0" />
                  </Button>
                  <h1 tabIndex="-1" className="min-w-0 break-words text-lg font-semibold leading-tight tracking-tight text-balance [overflow-wrap:anywhere]"><bdi>{folder?.name || team?.name}</bdi></h1>
                </div>
              ) : view === 'teams' ? (
                <p className="text-lg font-semibold text-foreground">{t('teamsDescription')}</p>
              ) : null}
              <div className="flex flex-wrap items-center gap-2">
                {view === 'teams' && !setupPending && (
                  <Button variant="link" size="sm" onClick={() => discover()} disabled={!!busy}>
                    {busy === 'teams' ? <Spinner /> : <RefreshCw />} {t('refresh')}
                  </Button>
                )}
                {view === 'browse' && !inSelect && (
                  <Button size="sm" onClick={event => {
                    flyToQueue(event.currentTarget.querySelector('svg'), { endScale: 0.8, describe: n => n === 1 ? t('queuedOne', { name: folder?.name || team?.name }) : t('queuedMany', { count: n }) })
                    startDownload(folder ? { scope: 'folder', folder } : { scope: 'team' })
                  }} disabled={!!busy}>
                    <Download className="size-3.5" /> {folder ? t('folderBackup') : t('teamBackup')}
                  </Button>
                )}
                {view === 'browse' && inSelect && (
                  <>
                    <Checkbox checked={allState === 'half' ? 'indeterminate' : allState === 'on'} onCheckedChange={onSelectAll} aria-label={t('selectAll')} />
                    <span className="text-xs font-semibold tabular-nums text-muted-foreground" role="status">
                      {t('ofSelected', { count: selCount, total: folders.length + files.length })}
                    </span>
                  </>
                )}
                {view === 'browse' && (
                  <Button
                    ref={selectBtnRef}
                    variant={inSelect ? 'default' : 'outline'} size="sm"
                    aria-pressed={inSelect}
                    onClick={() => (inSelect ? exitSelectMode() : setSelectMode(true))}
                  >
                    {inSelect ? <><Check className="size-3.5" /> {t('done')}</> : <><CheckCircle2 className="size-3.5" /> {t('select')}</>}
                  </Button>
                )}
              </div>
            </div>
          </div>}

          {view === 'settings' && (
            <div className="w-full">
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-md px-3 py-2.5">
                <Label htmlFor="setting-language">{t('language')}</Label>
                <Select dir={rtl ? 'rtl' : 'ltr'} value={language} onValueChange={async value => { if (await savePrefs({ language: value })) toast.success(translate(value, 'savedNotice'), { id: 'app-notice' }) }}>
                  <SelectTrigger id="setting-language" className="w-40 max-w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {LANGUAGES.map(item => (
                      <SelectItem key={item.code} value={item.code}>{item.native}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-md px-3 py-2.5">
                <Label htmlFor="setting-theme">{t('theme')}</Label>
                <Select dir={rtl ? 'rtl' : 'ltr'} value={preferences.theme} onValueChange={async value => { if (await savePrefs({ theme: value })) toast.success(t('savedNotice'), { id: 'app-notice' }) }}>
                  <SelectTrigger id="setting-theme" className="w-40 max-w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="system">{t('system')}</SelectItem>
                    <SelectItem value="light">{t('light')}</SelectItem>
                    <SelectItem value="dark">{t('dark')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-wrap items-start justify-between gap-4 rounded-md px-3 py-2.5">
                <div>
                  <h2 className="text-sm font-medium">{t('tokenSettings')}</h2>
                </div>
                <form onSubmit={saveTokenContinue} className="grid w-full max-w-xs gap-2.5">
                  <Label htmlFor="token-settings" className="sr-only">{t('newToken')}</Label>
                  <Input id="token-settings" type="password" value={token} onInput={e => { setToken(e.currentTarget.value); setTokenError('') }} placeholder="figd_…" autoComplete="off" aria-invalid={!!tokenError} />
                  {tokenError && <p role="alert" className="text-xs font-medium text-destructive">{tokenError}</p>}
                  <Button type="submit" className="justify-self-end" size="sm" disabled={!!busy}>{busy === 'token' ? <Spinner /> : null} {t(hasToken ? 'replaceToken' : 'newToken')}</Button>
                </form>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-4 rounded-md px-3 py-2.5">
                <div>
                  <h2 className="text-sm font-medium">{t('redoSetup')}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">{t('signInTitle')}</p>
                </div>
                <Button variant="outline" size="sm" onClick={redoSetup}><RotateCcw className="size-3.5" /> {t('redoSetup')}</Button>
              </div>
            </div>
          )}

          {view === 'teams' && (
            <div className="w-full">
              {setupPending && (
                <div className="flex flex-wrap items-center justify-between gap-3 bg-primary/5 px-3 py-3.5">
                  <div className="flex min-w-0 items-start gap-2.5">
                    <Loader2 className="mt-0.5 size-4 shrink-0 text-brand-text motion-safe:animate-spin" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-brand-text">{t('setupHeading')}</p>
                      <p className="mt-0.5 max-w-md text-xs leading-relaxed text-muted-foreground">{setupEscalated ? t('setupEscalated') : t('setupBody')}</p>
                    </div>
                  </div>
                </div>
              )}
              {setupFailed && (
                <div className="flex flex-wrap items-center justify-between gap-3 bg-[var(--figma-color-bg-danger-tertiary)] px-3 py-3.5">
                  <div className="flex min-w-0 items-start gap-2.5">
                    <AlertTriangle className="mt-0.5 size-4 shrink-0 text-destructive" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-destructive">{t('setupFailed')}</p>
                      {browserSetup.message && <p className="mt-0.5 max-w-md break-words text-xs leading-relaxed text-muted-foreground">{browserSetup.message}</p>}
                    </div>
                  </div>
                  <Button variant="outline" size="sm" onClick={retryBrowserSetup} disabled={!!busy}>
                    {busy === 'browser-setup' ? <Spinner /> : <RotateCcw className="size-3" />} {t('setupRetry')}
                  </Button>
                </div>
              )}
              {authRequired && (
                <div className="flex flex-wrap items-center justify-between gap-3 bg-primary/5 px-3 py-3.5">
                  <div>
                    <p className="text-sm font-semibold text-brand-text">{t('signInTitle')}</p>
                    <p className="mt-0.5 max-w-md text-xs leading-relaxed text-muted-foreground">{t('signInDescription')}</p>
                  </div>
                  <Button size="sm" onClick={() => openWizard('signin')}><ExternalLink className="size-3.5" /> {t('openSignIn')}</Button>
                </div>
              )}
              <div>
                {busy === 'teams' ? (
                  <SkeletonRows count={3} label={t('loading')} />
                ) : teams.map(value => (
                  <button key={value.id} className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-start transition-colors hover:bg-accent/60 disabled:opacity-50" onClick={() => chooseTeam(value)} disabled={!!busy}>
                    <TeamAvatar team={value} />
                    <span className="min-w-0 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                    <ChevronRight className="size-4 shrink-0 text-muted-foreground rtl:-scale-x-100" aria-hidden="true" />
                  </button>
                ))}
              </div>
              {!teams.length && setupPending && (
                <div role="status" className="px-3 py-8 text-center text-sm text-muted-foreground">{t('teamsPending')}</div>
              )}
              {!teams.length && !setupBlocked && busy !== 'teams' && (
                <div className="px-3 py-8 text-center text-sm text-muted-foreground">{t('noTeams')}</div>
              )}
            </div>
          )}

          {view === 'browse' && (
            <div className="w-full">
            <div>
              {loadingBrowse && <SkeletonRows count={7} label={t('loading')} />}
              {sortedFolders.map(value => inSelect ? (
                  <div key={value.id} className={'flex flex-wrap items-center gap-3 rounded-md px-3 py-2.5 ' + (folderSelected(value.id) ? 'bg-primary/5' : '')}>
                    <Checkbox checked={folderSelected(value.id)} onCheckedChange={() => toggleFolder(value)} aria-label={t('ariaSelectItem', { name: value.name })} className="shrink-0" />
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"><Folder className="size-4" /></span>
                    <span className="min-w-28 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                    <button className="flex flex-none items-center gap-1 rounded px-1.5 py-1 text-xs font-semibold text-brand-text hover:underline" onClick={() => browseFolder(value)} disabled={!!busy} aria-label={t('ariaOpen', { name: value.name })}>
                      {t('open')} <ChevronRight className="size-3.5 rtl:-scale-x-100" aria-hidden="true" />
                    </button>
                  </div>
                ) : (
                  <div key={value.id} data-download-row="" className="flex flex-wrap items-center gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-accent/60">
                    <button className="flex min-w-0 flex-1 items-center gap-3 text-start" onClick={() => browseFolder(value)} disabled={!!busy} aria-label={t('ariaOpen', { name: value.name })}>
                      <span data-row-tile="" className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"><Folder className="size-4" /></span>
                      <span className="min-w-0 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                    </button>
                    <div className="flex shrink-0 items-center gap-3">
                      <Button variant="ghost" size="icon-sm" onClick={event => { flyToQueue(event.currentTarget.closest('[data-download-row]')?.querySelector('[data-row-tile]'), { describe: n => n === 1 ? t('queuedOne', { name: value.name }) : t('queuedMany', { count: n }) }); startDownload({ scope: 'folder', folder: value }) }} disabled={!!busy} aria-label={t('ariaBackupItem', { name: value.name })} title={t('ariaBackupItem', { name: value.name })}>
                        <Download className="size-4" aria-hidden="true" />
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => browseFolder(value)} disabled={!!busy} aria-label={t('ariaOpen', { name: value.name })} title={t('ariaOpen', { name: value.name })}>
                        <ChevronRight className="size-4 text-muted-foreground rtl:-scale-x-100" aria-hidden="true" />
                      </Button>
                    </div>
                  </div>
                ))}
                {sortedFiles.map(value => inSelect ? (
                  <div key={value.key} className={'flex flex-wrap items-center gap-3 rounded-md px-3 py-2.5 ' + (fileSelected(value.key) ? 'bg-primary/5' : '')}>
                    <Checkbox checked={fileSelected(value.key)} onCheckedChange={() => toggleFile(value)} aria-label={t('ariaSelectItem', { name: value.name })} className="shrink-0" />
                    <FileIcon editorType={value.editorType} />
                    <span className="min-w-28 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                  </div>
                ) : (
                  <div key={value.key} data-download-row="" className="flex flex-wrap items-center gap-3 rounded-md px-3 py-2.5 transition-colors hover:bg-accent/60">
                    <FileIcon editorType={value.editorType} data-row-tile="" />
                    <span className="min-w-28 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                    <Button variant="outline" size="sm" onClick={event => { flyToQueue(event.currentTarget.closest('[data-download-row]')?.querySelector('[data-row-tile]'), { describe: n => n === 1 ? t('queuedOne', { name: value.name }) : t('queuedMany', { count: n }) }); startDownload({ scope: 'file', folder, file_key: value.key, name: value.name, editor_type: value.editorType }) }} disabled={!!busy} aria-label={t('ariaDownloadItem', { name: value.name })}>
                      {busy === 'download' ? <Spinner /> : <Download className="size-3.5" />} {t('downloadFile')}
                    </Button>
                  </div>
                ))}
              </div>
              {!loadingBrowse && !folders.length && !files.length && <div className="px-3 py-8 text-center text-sm leading-relaxed text-muted-foreground text-pretty">{t(folder ? 'emptyFolder' : 'emptyTeam')}</div>}
            </div>
          )}
        </>
      }
      </main>

      {nativeWin && !maximized && (
        <div aria-hidden="true">
          {RESIZE_EDGES.map(([classes, edge]) => (
            <div
              key={edge}
              className={'fixed z-50 ' + classes}
              onMouseDown={() => window.pywebview.api.begin_resize(edge)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default App
