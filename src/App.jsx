import { useEffect, useMemo, useRef, useState } from 'react'
import { Popover as PopoverPrimitive } from 'radix-ui'
import {
  AlertTriangle, Check, CheckCircle2, ChevronRight, Clock, Download, ExternalLink,
  Folder, Loader2, PenTool, RefreshCw, RotateCcw, Settings as SettingsIcon,
  Square, X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { translate } from './i18n'

const DONE_STATES = ['saved', 'exists', 'renamed']
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms))
const firstLine = (text) => String(text || '').split('\n')[0].replace(/^Error:\s*/, '')
const isSigninIssue = (text) => /sign-in|background editor.*403/i.test(String(text || ''))

function bridgeReady() {
  if (window.pywebview?.api?.bootstrap) return Promise.resolve(window.pywebview.api)
  return new Promise(resolve => window.addEventListener('pywebviewready', () => resolve(window.pywebview.api), { once: true }))
}

function Ring({ value, label, name }) {
  const r = 14
  const c = 2 * Math.PI * r
  return (
    <span role="progressbar" aria-label={name} aria-valuemin="0" aria-valuemax="100" aria-valuenow={value} className="relative inline-block size-9 flex-none">
      <svg width="36" height="36" viewBox="0 0 36 36" className="-rotate-90" aria-hidden="true">
        <circle cx="18" cy="18" r={r} fill="none" strokeWidth="3" className="stroke-muted" />
        <circle cx="18" cy="18" r={r} fill="none" strokeWidth="3" strokeLinecap="round" className="stroke-primary motion-safe:transition-[stroke-dasharray] motion-safe:duration-150" strokeDasharray={`${(c * value) / 100} ${c}`} />
      </svg>
      <span aria-hidden="true" className="absolute inset-0 grid place-items-center text-[10px] font-bold tabular-nums">{label}%</span>
    </span>
  )
}

/* Tri-state select-all (role=checkbox + aria-checked="mixed"; 24px hit target) */
function TriCheckbox({ state, onClick, label }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={state === 'on' ? true : state === 'half' ? 'mixed' : false}
      aria-label={label}
      onClick={onClick}
      className={
        'grid size-6 place-items-center rounded-md border outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background ' +
        (state === 'off' ? 'border-input bg-background hover:border-primary/60' : 'border-primary bg-primary text-primary-foreground hover:bg-primary/90')
      }
    >
      {state === 'on' && <Check className="size-3.5" />}
      {state === 'half' && <span className="h-0.5 w-2.5 rounded-full bg-current" />}
    </button>
  )
}

function RowCheckbox({ checked, label, onToggle }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      aria-label={label}
      onClick={onToggle}
      className={
        'grid size-6 shrink-0 place-items-center rounded-md border outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background ' +
        (checked ? 'border-primary bg-primary text-primary-foreground' : 'border-input bg-background hover:border-primary/60')
      }
    >
      {checked && <Check className="size-3.5" />}
    </button>
  )
}

function TeamAvatar({ team }) {
  const [failed, setFailed] = useState(false)
  useEffect(() => setFailed(false), [team.avatar])
  const avatar = typeof team.avatar === 'string' && team.avatar.startsWith('data:image/') ? team.avatar : ''
  return (
    <span className="flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-primary/10 text-sm font-bold text-brand-text" aria-hidden="true">
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
  const [notice, setNotice] = useState('')
  const [progress, setProgress] = useState({ running: false, phase: 'idle', items: [], total: 0, saved: 0, existing: 0, skipped: 0, failed: 0, message: '', destination: '', finished: false })
  const [selectMode, setSelectMode] = useState(false)
  const [selection, setSelection] = useState({}) // teamId -> { folders: [], files: [] }
  const [queue, setQueue] = useState([])
  const [queueOpen, setQueueOpen] = useState(false)
  const [queueRunning, setQueueRunning] = useState(false)
  const [confirmCancel, setConfirmCancel] = useState(false)
  const queueRef = useRef([])
  const queueRunnerRef = useRef(false)
  const stopAfterCurrentRef = useRef(false)
  const selectBtnRef = useRef(null)
  const runIdRef = useRef(0)
  const language = preferences.language
  const t = (key, values) => translate(language, key, values)
  const countCopy = (key, count) => t(count === 1 ? `${key}One` : key, { count })
  const appearance = preferences.theme === 'system' ? (systemDark ? 'dark' : 'light') : preferences.theme
  const rtl = language === 'fa'
  const [sortedFolders, sortedFiles] = useMemo(() => {
    const collator = new Intl.Collator(language, { sensitivity: 'base', numeric: true })
    const byName = (a, b) => collator.compare(a.name || '', b.name || '')
    return [[...folders].sort(byName), [...files].sort(byName)]
  }, [folders, files, language])
  const nativeMac = api && window.pywebview?.platform === 'cocoa'

  const teamSel = team ? (selection[team.id] || { folders: [], files: [] }) : { folders: [], files: [] }
  const selCount = teamSel.folders.length + teamSel.files.length
  const pillVisible = view === 'browse' && selCount > 0 && !queueOpen

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

  /* Esc closes the popover through Radix, or exits select mode. */
  useEffect(() => {
    const onKey = (e) => {
      if (e.key !== 'Escape') return
      if (!queueOpen && selectMode) { setSelectMode(false); selectBtnRef.current?.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [queueOpen, selectMode])

  async function call(label, action) {
    setBusy(label); setError(''); setNotice('')
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
      setNotice(t('tokenSavedNotice'))
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
    const result = await call('folders', () => api.folders(value.id))
    if (!result) return
    setTeam(value); setFolders(result.folders || []); setFolder(null); setTrail([]); setFiles([])
    setSelectMode(false)
    setView('browse')
    if (result.legacy) setNotice(t('legacyNotice'))
  }

  async function browseFolder(value, path = [...trail, value]) {
    const result = await call('browse', async () => {
      const children = await api.subfolders(value.id)
      const fileResult = await api.files(value.id)
      return { children, fileResult }
    })
    if (!result) return
    setFolder(value); setTrail(path); setFolders(result.children.folders || [])
    setFiles(result.fileResult.files || [])
    if (result.children.unavailable || result.fileResult.unavailable) setNotice(t('folderRestricted'))
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
      files: fileSelected(f.key) ? cur.files.filter(x => x.key !== f.key) : [...cur.files, { key: f.key, name: f.name, folder }],
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
        folders: [...cur.folders.filter(f => !folders.some(v => v.id === f.id)), ...folders.filter(f => !folderSelected(f.id))],
        files: [...cur.files.filter(f => !files.some(v => v.key === f.key)), ...files.filter(f => !fileSelected(f.key)).map(f => ({ key: f.key, name: f.name, folder }))],
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
    setQueueRunning(true)
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
          await api.start_download({ team: item.team, ...sel })
          const s = await waitForRunEnd(runId)
          if (s.cancelled) break
          if (s.warning) setNotice(backendWarning(s.warning))
          if (s.phase === 'attention' || isSigninIssue(s.message)) {
            updateQueueItem(item.id, { status: 'failed', detail: t('interrupted') })
            routeToSignin()
            break
          }
          updateQueueItem(item.id, {
            status: s.phase === 'stopped' ? 'stopped' : s.phase === 'error' || s.failed > 0 ? 'failed' : 'done',
            detail: s.phase === 'error' || s.failed > 0 ? firstLine(s.message) : '',
          })
        } catch (err) {
          const msg = firstLine(err)
          if (isSigninIssue(msg)) {
            updateQueueItem(item.id, { status: 'failed', detail: t('interrupted') })
            routeToSignin()
            break
          }
          updateQueueItem(item.id, { status: 'failed', detail: msg })
        }
        if (stopAfterCurrentRef.current) break
      }
    } finally {
      queueRunnerRef.current = false
      stopAfterCurrentRef.current = false
      setQueueRunning(false)
    }
  }
  function enqueueItems(items, showDetails = true) {
    changeQueue(current => queueRunnerRef.current ? [...current, ...items] : items)
    setConfirmCancel(false)
    if (showDetails) setQueueOpen(true)
    void runQueue()
  }
  function startSelectionBackup() {
    if (!team || selCount === 0) return
    const batch = Date.now()
    const items = [
      ...teamSel.folders.map((f, i) => ({ id: `f-${batch}-${i}`, kind: 'folder', name: f.name, team, folder: f, status: 'queued', detail: '' })),
      ...teamSel.files.map((f, i) => ({ id: `k-${batch}-${i}`, kind: 'file', name: f.name, team, folder: f.folder, file_key: f.key, status: 'queued', detail: '' })),
    ]
    clearSelection()
    enqueueItems(items)
  }
  function retryItem(id) {
    updateQueueItem(id, { status: 'queued', detail: '' })
    void runQueue()
  }
  function resumeQueue() {
    changeQueue(q => q.map(it => ['failed', 'stopped'].includes(it.status) ? { ...it, status: 'queued', detail: '' } : it))
    void runQueue()
  }
  function cancelRemaining() {
    changeQueue(q => q.filter(it => it.status !== 'queued'))
    setConfirmCancel(false)
  }
  async function stopCurrent() {
    stopAfterCurrentRef.current = true
    try { await api.stop_download() } catch { /* noop */ }
  }

  function openSettings() { setSettingsReturn(view === 'settings' ? 'teams' : view); setQueueOpen(false); setView('settings'); setError(''); setNotice('') }
  function leaveSettings() { setView(settingsReturn || 'teams'); setToken(''); setTokenError(''); setError(''); setNotice('') }
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
      status: 'queued', detail: '',
    }], false)
  }

  const doneCount = progress.items.filter(item => DONE_STATES.includes(item.status)).length
  const percentage = progress.total ? Math.round((doneCount / progress.total) * 100) : 0
  const queuedCount = queue.filter(it => it.status === 'queued').length
  const failedCount = queue.filter(it => it.status === 'failed' || it.status === 'stopped').length
  const activeItem = queue.find(it => it.status === 'running')
  const barTitle = progress.running
    ? (activeItem ? `${t('progressTitle')} — ${activeItem.name}` : t('progressTitle'))
    : progress.phase === 'stopped' ? t('barStopped')
      : progress.total ? (progress.failed ? t('progressPartial') : t('barIdle'))
      : t('queueTitle')
  const barSub = progress.total
    ? `${t(progress.total === 1 ? 'progressCountOne' : 'progressCount', { done: doneCount, total: progress.total })}${progress.message ? ' · ' + backendMsg(progress.message) : ''}`
    : queue.length ? countCopy('itemsCount', queue.length) : ''

  const Spinner = () => <Loader2 className="size-4 motion-safe:animate-spin" aria-hidden="true" />

  /* Backend emits a few fixed English strings; surface them in the UI language */
  function backendMsg(msg) {
    const m = String(msg || '')
    if (m === 'Collecting files…') return t('collectingFiles')
    if (m === 'Download queue is ready') return t('queueReady')
    return m
  }
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
    <Card className="mx-auto w-full max-w-xl p-5 sm:p-6">
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
            <p className="rounded-lg bg-muted px-3.5 py-2.5 text-xs leading-relaxed text-muted-foreground">{t('tokenPrivacy')}</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <span className="me-auto text-[11px] text-muted-foreground">
                {t('language')}: <b className="font-semibold text-foreground">{language === 'en' ? t('english') : t('persian')}</b> · <button type="button" className="font-semibold text-brand-text hover:underline" onClick={openSettings}>{t('settings')}</button>
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
            <div className="rounded-lg bg-muted px-3.5 py-2.5 text-sm leading-relaxed text-muted-foreground text-pretty">{t('signInDescription')}</div>
            <div className="mt-2 flex flex-wrap items-center justify-end gap-2">
              <Button variant="ghost" onClick={completeSetup}>{t('signinLater')}</Button>
              <Button onClick={signInNow} disabled={!!busy}>
                {busy === 'sign-in' ? <Spinner /> : loginOpen ? <CheckCircle2 className="size-4" /> : <ExternalLink className="size-4" />}
                {loginOpen ? t('iveSignedIn') : t('openSignIn')}
              </Button>
            </div>
          </div>
        </>
      )}
    </Card>
  )

  /* ---------- selection pill ---------- */
  const pill = pillVisible && (
    <div className="fixed inset-x-4 bottom-4 z-40 mx-auto flex max-w-[560px] flex-wrap items-center justify-center gap-2.5 rounded-xl border bg-card/95 px-3 py-2 shadow-lg backdrop-blur">
      <span className="min-w-0 text-xs font-semibold leading-tight" role="status">
        {countCopy('itemsCount', selCount)}
        <small className="block text-[10.5px] font-medium text-muted-foreground">{countCopy('folderCount', teamSel.folders.length)} · {countCopy('fileCount', teamSel.files.length)}</small>
      </span>
      <Button size="sm" onClick={startSelectionBackup} disabled={!!busy}>
        {busy === 'download' ? <Spinner /> : <Download className="size-3.5" />}
        {queue.some(item => item.status === 'running' || item.status === 'queued') ? t('addToQueue') : countCopy('backUpItems', selCount)}
      </Button>
      <button aria-label={t('clearSelection')} onClick={clearSelection} className="grid size-8 place-items-center rounded-full text-muted-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring">
        <X className="size-3.5" />
      </button>
    </div>
  )

  /* ---------- download manager popover ---------- */
  const downloadManager = (
    <div className="flex min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <h2 className="min-w-0 flex-1 text-sm font-semibold">{t('downloadManagerTitle')}</h2>
        <span className="text-xs tabular-nums text-muted-foreground">{countCopy('itemsCount', queue.length)}</span>
        <button type="button" aria-label={t('close')} onClick={() => setQueueOpen(false)} className="grid size-7 flex-none place-items-center rounded-md text-muted-foreground hover:bg-accent focus-visible:outline-2 focus-visible:outline-ring">
          <X className="size-3.5" aria-hidden="true" />
        </button>
      </div>
      {(progress.running || progress.total > 0 || queue.length > 0) && (
        <div role="status" className="flex items-center gap-3 border-b px-4 py-3">
          <Ring value={percentage} label={percentage} name={t('progressTitle')} />
          <span className="min-w-0 flex-1">
            <span className="block truncate text-xs font-bold">{barTitle}</span>
            <span className="block truncate text-[10.5px] text-muted-foreground">{barSub}</span>
          </span>
        </div>
      )}
      {progress.destination && queue.length > 0 && (
        <p dir="ltr" title={progress.destination} className="truncate border-b bg-muted/40 px-4 py-2 text-xs text-muted-foreground">{t('destination', { path: progress.destination + '/' })}</p>
      )}
      <div className="max-h-[min(320px,50vh)] divide-y overflow-y-auto">
            {queue.map(item => (
              <div key={item.id} className="flex flex-wrap items-center gap-2.5 px-4 py-2.5">
                <span className={'grid size-[22px] flex-none place-items-center rounded-full ' + (
                  item.status === 'done' ? 'bg-success/15 text-success'
                    : item.status === 'running' ? 'bg-primary/15 text-brand-text'
                    : item.status === 'failed' ? 'bg-destructive/15 text-destructive'
                    : 'bg-muted text-muted-foreground'
                )}>
                  {item.status === 'done' ? <CheckCircle2 className="size-3" />
                    : item.status === 'running' ? <Loader2 className="size-3 motion-safe:animate-spin" />
                    : item.status === 'failed' ? <AlertTriangle className="size-3" />
                    : item.status === 'stopped' ? <Square className="size-3" />
                    : <Clock className="size-3" />}
                </span>
                <span aria-hidden="true" className={'flex-none rounded-full px-2 py-0.5 text-[10px] font-semibold ' + (item.kind !== 'file' ? 'bg-primary/15 text-brand-text' : 'bg-muted text-muted-foreground')}>
                  {item.kind === 'team' ? t('kindTeam') : item.kind === 'folder' ? t('kindFolder') : t('kindFile')}
                </span>
                <span className="min-w-28 flex-1 break-words [overflow-wrap:anywhere]">
                  <span className="block text-sm font-medium leading-snug"><bdi>{item.name}</bdi></span>
                  {item.detail && <span dir="auto" className="mt-0.5 block break-words text-xs leading-snug text-muted-foreground [overflow-wrap:anywhere]">{item.detail}</span>}
                </span>
                {(item.status === 'failed' || item.status === 'stopped') && (
                  <Button variant="outline" size="sm" onClick={() => retryItem(item.id)}><RotateCcw className="size-3" /> {t('retry')}</Button>
                )}
                <span className={'flex-none text-end text-xs font-semibold ' + (item.status === 'done' ? 'text-success' : item.status === 'failed' ? 'text-destructive' : item.status === 'running' ? 'text-brand-text' : 'text-muted-foreground')}>
                  {item.status === 'done' ? t('statusSaved') : item.status === 'running' ? t('running') : item.status === 'failed' ? t('statusFailed') : item.status === 'stopped' ? t('statusStopped') : t('statusQueued')}
                </span>
              </div>
            ))}
            {!queue.length && (
              <div className="px-4 py-8 text-center text-sm text-muted-foreground">
                <Download className="mx-auto mb-2 size-5 opacity-60" aria-hidden="true" />
                {t('downloadManagerEmpty')}
              </div>
            )}
      </div>
      <div className="flex flex-wrap items-center gap-2 border-t px-3 py-2.5">
            {(failedCount > 0 || queuedCount > 0) && !queueRunning && (
              <Button variant="outline" size="sm" onClick={resumeQueue}><RotateCcw className="size-3" /> {t(failedCount > 0 ? 'resumeQueue' : 'continueQueue')}</Button>
            )}
            {queuedCount > 0 && (
              <div className="flex flex-wrap items-center gap-2">
                <Button variant={confirmCancel ? 'destructive' : 'ghost'} size="sm" onClick={confirmCancel ? cancelRemaining : () => setConfirmCancel(true)}>
                  <X className="size-3" /> {confirmCancel ? countCopy('confirmCancelRemaining', queuedCount) : `${t('cancelRemaining')} (${queuedCount})`}
                </Button>
                {confirmCancel && <Button variant="ghost" size="sm" onClick={() => setConfirmCancel(false)}>{t('keepQueued')}</Button>}
              </div>
            )}
            <span className="flex-1" />
            {progress.running && (
              <Button variant="outline" size="sm" onClick={stopCurrent}><Square className="size-3" /> {t('stop')}</Button>
            )}
        <Button variant="ghost" size="sm" onClick={() => api.open_downloads()}><ExternalLink className="size-3.5" /> {t('openDownloads')}</Button>
        {queue.length > 0 && <Button size="sm" onClick={() => api.open_destination()}><ExternalLink className="size-3.5" /> {t('openDestination')}</Button>}
      </div>
    </div>
  )

  const inSelect = view === 'browse' && selectMode

  return (
    <div className={'flex min-h-screen flex-col' + (nativeMac ? ' native-mac-titlebar' : '')}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-3 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:shadow">{t('skipToContent')}</a>

      <header className="pywebview-drag-region sticky top-0 z-30 border-b bg-background/80 backdrop-blur">
        <div className="pywebview-drag-region app-header-inner mx-auto flex h-12 w-full max-w-[680px] items-center gap-2.5 px-4">
          {view === 'settings' ? (
            <div className="flex min-w-0 items-center gap-1">
              <Button variant="ghost" size="icon-lg" aria-label={t('back')} title={t('back')} onClick={leaveSettings}>
                <ChevronRight className="size-4 rotate-180 rtl:rotate-0" aria-hidden="true" />
              </Button>
              <span className="text-sm font-medium tracking-tight">{t('settingsTitle')}</span>
            </div>
          ) : <span className="text-sm font-medium tracking-tight">Fig Backup</span>}
          <div className="ms-auto flex items-center gap-1">
            {view !== 'wizard' && view !== 'settings' && (
              <PopoverPrimitive.Root open={queueOpen} onOpenChange={setQueueOpen}>
                <PopoverPrimitive.Trigger asChild>
                  <Button variant="ghost" size="icon-lg" aria-label={t('downloadManagerTitle')} title={t('downloadManagerTitle')} aria-expanded={queueOpen} aria-controls="download-manager">
                    <Download className="size-4" aria-hidden="true" />
                  </Button>
                </PopoverPrimitive.Trigger>
                <PopoverPrimitive.Portal>
                  <PopoverPrimitive.Content id="download-manager" aria-label={t('downloadManagerTitle')} side="bottom" align="end" sideOffset={8} collisionPadding={8} className="z-50 w-[min(420px,calc(100vw-24px))] overflow-hidden rounded-xl border bg-popover text-popover-foreground shadow-xl outline-none">
                    {downloadManager}
                  </PopoverPrimitive.Content>
                </PopoverPrimitive.Portal>
              </PopoverPrimitive.Root>
            )}
            {view !== 'wizard' && view !== 'settings' && (
              <Button variant="ghost" size="icon-lg" aria-label={t('settings')} title={t('settings')} onClick={openSettings}>
                <SettingsIcon className="size-4" aria-hidden="true" />
              </Button>
            )}
          </div>
        </div>
      </header>

      <main id="main" className={'mx-auto w-full max-w-[680px] flex-1 px-4 pt-7 ' + (pillVisible ? 'pb-28' : 'pb-10')}>
        {error && (
          <div role="alert" className="mb-4 flex items-start gap-2.5 rounded-lg border border-[var(--figma-color-border-danger)] bg-[var(--figma-color-bg-danger-tertiary)] px-3.5 py-2.5 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            <span className="min-w-0 flex-1 break-words">{error} {errorHelp(error)}</span>
            <button onClick={() => setError('')} aria-label={t('close')} className="grid size-8 shrink-0 place-items-center rounded-md hover:bg-destructive/15 focus-visible:outline-2 focus-visible:outline-ring"><X className="size-3.5" /></button>
          </div>
        )}
        {notice && (
          <div role="status" className="mb-4 flex items-start gap-2.5 rounded-lg border border-primary/25 bg-primary/10 px-3.5 py-2.5 text-sm text-brand-text">
            <span className="min-w-0 flex-1 break-words">{notice}</span>
            <button onClick={() => setNotice('')} aria-label={t('close')} className="grid size-8 shrink-0 place-items-center rounded-md hover:bg-primary/15 focus-visible:outline-2 focus-visible:outline-ring"><X className="size-3.5" /></button>
          </div>
        )}
        {!ready ? (
          <div role="status" className="flex items-center justify-center gap-2.5 py-24 text-muted-foreground"><Spinner /> {t('loading')}</div>
        ) : view === 'wizard' ? wizard : <>
          {view !== 'settings' && <div className="mb-5">
            {view === 'browse' && (
              <nav className="mb-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground" aria-label={t('breadcrumb')}>
                <button className="rounded font-medium text-brand-text hover:underline" onClick={() => setView('teams')}>{t('teamsTitle')}</button>
                {trail.length > 0 && <><span aria-hidden="true">/</span><button className="rounded font-medium text-brand-text hover:underline" onClick={() => backTo(-1)}><bdi>{team?.name}</bdi></button></>}
                {trail.slice(0, -1).map((item, index) => (
                  <span key={item.id} className="flex items-center gap-1.5">
                    <span aria-hidden="true">/</span>
                    <button className="rounded font-medium text-brand-text hover:underline" onClick={() => backTo(index)}><bdi>{item.name}</bdi></button>
                  </span>
                ))}
              </nav>
            )}
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              {view === 'browse' ? (
                <div className="flex min-w-0 items-center gap-2">
                  <Button variant="ghost" size="icon-sm" aria-label={t('back')} onClick={() => (trail.length > 1 ? backTo(trail.length - 2) : trail.length ? backTo(-1) : setView('teams'))}>
                    <ChevronRight className="rotate-180 rtl:rotate-0" />
                  </Button>
                  <h1 tabIndex="-1" className="min-w-0 break-words text-xl font-bold leading-tight tracking-tight text-balance sm:text-2xl [overflow-wrap:anywhere]"><bdi>{folder?.name || team?.name}</bdi></h1>
                </div>
              ) : view === 'teams' ? (
                <h1 tabIndex="-1" className="text-2xl font-bold tracking-tight">{t('teamsTitle')}</h1>
              ) : null}
              <div className="flex flex-wrap items-center gap-2">
                {view === 'teams' && (
                  <Button variant="outline" size="sm" onClick={() => discover()} disabled={!!busy}>
                    {busy === 'teams' ? <Spinner /> : <RefreshCw />} {t('refresh')}
                  </Button>
                )}
                {view === 'browse' && !inSelect && (
                  <Button size="sm" onClick={() => startDownload(folder ? { scope: 'folder', folder } : { scope: 'team' })} disabled={!!busy}>
                    <Download className="size-3.5" /> {folder ? t('folderBackup') : t('teamBackup')}
                  </Button>
                )}
                {view === 'browse' && inSelect && (
                  <>
                    <TriCheckbox state={allState} onClick={onSelectAll} label={t('selectAll')} />
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
            {view === 'teams' && <p className="mt-1 text-sm text-muted-foreground">{t('teamsDescription')}</p>}
          </div>}

          {view === 'settings' && (
            <Card className="w-full gap-0 py-1">
              <div className="flex flex-wrap items-center justify-between gap-4 border-b px-5 py-4">
                <Label htmlFor="setting-language">{t('language')}</Label>
                <Select dir={rtl ? 'rtl' : 'ltr'} value={language} onValueChange={async value => { if (await savePrefs({ language: value })) setNotice(translate(value, 'savedNotice')) }}>
                  <SelectTrigger id="setting-language" className="w-40 max-w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="fa">فارسی</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-4 border-b px-5 py-4">
                <Label htmlFor="setting-theme">{t('theme')}</Label>
                <Select dir={rtl ? 'rtl' : 'ltr'} value={preferences.theme} onValueChange={async value => { if (await savePrefs({ theme: value })) setNotice(t('savedNotice')) }}>
                  <SelectTrigger id="setting-theme" className="w-40 max-w-full"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="system">{t('system')}</SelectItem>
                    <SelectItem value="light">{t('light')}</SelectItem>
                    <SelectItem value="dark">{t('dark')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-wrap items-start justify-between gap-4 border-b px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold">{t('tokenSettings')}</h2>
                </div>
                <form onSubmit={saveTokenContinue} className="grid w-full max-w-xs gap-2.5">
                  <Label htmlFor="token-settings" className="sr-only">{t('newToken')}</Label>
                  <Input id="token-settings" type="password" value={token} onInput={e => { setToken(e.currentTarget.value); setTokenError('') }} placeholder="figd_…" autoComplete="off" aria-invalid={!!tokenError} />
                  {tokenError && <p role="alert" className="text-xs font-medium text-destructive">{tokenError}</p>}
                  <Button type="submit" className="justify-self-end" size="sm" disabled={!!busy}>{busy === 'token' ? <Spinner /> : null} {t(hasToken ? 'replaceToken' : 'newToken')}</Button>
                </form>
              </div>
              <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-4">
                <div>
                  <h2 className="text-sm font-semibold">{t('redoSetup')}</h2>
                  <p className="mt-1 text-xs text-muted-foreground">{t('signInTitle')}</p>
                </div>
                <Button variant="outline" size="sm" onClick={redoSetup}><RotateCcw className="size-3.5" /> {t('redoSetup')}</Button>
              </div>
            </Card>
          )}

          {view === 'teams' && (
            <Card className="w-full gap-0 py-1">
              <div className="flex items-center justify-between border-b px-5 py-3.5">
                <h2 className="text-sm font-semibold">{t('teamsTitle')}</h2>
                <span className="text-xs tabular-nums text-muted-foreground">{countCopy('teamCount', teams.length)}</span>
              </div>
              {authRequired && (
                <div className="flex flex-wrap items-center justify-between gap-3 border-b bg-primary/5 px-5 py-3.5">
                  <div>
                    <p className="text-sm font-semibold text-brand-text">{t('signInTitle')}</p>
                    <p className="mt-0.5 max-w-md text-xs leading-relaxed text-muted-foreground">{t('signInDescription')}</p>
                  </div>
                  <Button size="sm" onClick={() => openWizard('signin')}><ExternalLink className="size-3.5" /> {t('openSignIn')}</Button>
                </div>
              )}
              <div className="divide-y">
                {teams.map(value => (
                  <button key={value.id} className="flex w-full items-center gap-3 px-5 py-3 text-start transition-colors hover:bg-accent/60 disabled:opacity-50" onClick={() => chooseTeam(value)} disabled={!!busy}>
                    <TeamAvatar team={value} />
                    <span className="min-w-0 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                    <ChevronRight className="size-4 shrink-0 text-muted-foreground rtl:-scale-x-100" aria-hidden="true" />
                  </button>
                ))}
              </div>
              {!teams.length && <div className="px-5 py-8 text-center text-sm text-muted-foreground">{t('noTeams')}</div>}
            </Card>
          )}

          {view === 'browse' && (
            <Card className="w-full gap-0 py-1">
              <div className="divide-y">
                {sortedFolders.map(value => inSelect ? (
                  <div key={value.id} className={'flex flex-wrap items-center gap-3 px-5 py-3 ' + (folderSelected(value.id) ? 'bg-primary/5' : '')}>
                    <RowCheckbox checked={folderSelected(value.id)} label={t('ariaSelectItem', { name: value.name })} onToggle={() => toggleFolder(value)} />
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"><Folder className="size-4" /></span>
                    <span className="min-w-28 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                    <button className="flex flex-none items-center gap-1 rounded px-1.5 py-1 text-xs font-semibold text-brand-text hover:underline" onClick={() => browseFolder(value)} disabled={!!busy} aria-label={t('ariaOpen', { name: value.name })}>
                      {t('open')} <ChevronRight className="size-3.5 rtl:-scale-x-100" aria-hidden="true" />
                    </button>
                  </div>
                ) : (
                  <div key={value.id} className="flex flex-wrap items-center gap-3 px-5 py-3 transition-colors hover:bg-accent/40">
                    <button className="flex min-w-44 flex-1 items-center gap-3 text-start" onClick={() => browseFolder(value)} disabled={!!busy} aria-label={t('ariaOpen', { name: value.name })}>
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground"><Folder className="size-4" /></span>
                      <span className="min-w-0 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                      <ChevronRight className="size-4 shrink-0 text-muted-foreground rtl:-scale-x-100" aria-hidden="true" />
                    </button>
                    <Button variant="outline" size="sm" onClick={() => startDownload({ scope: 'folder', folder: value })} disabled={!!busy} aria-label={t('ariaBackupItem', { name: value.name })}>{t('backup')}</Button>
                  </div>
                ))}
                {sortedFiles.map(value => inSelect ? (
                  <div key={value.key} className={'flex flex-wrap items-center gap-3 px-5 py-3 ' + (fileSelected(value.key) ? 'bg-primary/5' : '')}>
                    <RowCheckbox checked={fileSelected(value.key)} label={t('ariaSelectItem', { name: value.name })} onToggle={() => toggleFile(value)} />
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-brand-text"><PenTool className="size-4" /></span>
                    <span className="min-w-28 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                  </div>
                ) : (
                  <div key={value.key} className="flex flex-wrap items-center gap-3 px-5 py-3 transition-colors hover:bg-accent/40">
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-brand-text"><PenTool className="size-4" /></span>
                    <span className="min-w-28 flex-1 break-words text-sm font-medium leading-snug [overflow-wrap:anywhere]"><bdi>{value.name}</bdi></span>
                    <Button variant="outline" size="sm" onClick={() => startDownload({ scope: 'file', folder, file_key: value.key, name: value.name })} disabled={!!busy} aria-label={t('ariaDownloadItem', { name: value.name })}>
                      {busy === 'download' ? <Spinner /> : <Download className="size-3.5" />} {t('downloadFile')}
                    </Button>
                  </div>
                ))}
              </div>
              {!folders.length && !files.length && <div className="px-5 py-8 text-center text-sm leading-relaxed text-muted-foreground text-pretty">{t(folder ? 'emptyFolder' : 'emptyTeam')}</div>}
            </Card>
          )}
        </>
      }
      </main>

      {pill}
    </div>
  )
}

export default App
