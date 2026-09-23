import { h, render, Fragment } from 'preact'
import { useEffect, useState } from 'preact/hooks'
import { Button, Textbox, IconFolder16, IconDesign16, IconCheck16, IconWarning16 } from '@create-figma-plugin/ui'
import '@create-figma-plugin/ui/css/base.css'
import '@create-figma-plugin/ui/css/theme.css'
import { translate } from './i18n'
import './style.css'

const blankProgress = { running: false, phase: 'idle', items: [], current: 0, total: 0, saved: 0, existing: 0, skipped: 0, failed: 0, message: '', warning: '', destination: '' }
const statusKeys = { queued: 'statusQueued', checking: 'statusChecking', opening: 'statusOpening', preparing: 'statusPreparing', saving: 'statusSaving', retrying: 'statusRetrying', saved: 'statusSaved', exists: 'statusExists', renamed: 'statusRenamed', skipped: 'statusSkipped', failed: 'statusFailed' }

function bridgeReady() {
  if (window.pywebview?.api?.bootstrap) return Promise.resolve(window.pywebview.api)
  return new Promise(resolve => window.addEventListener('pywebviewready', () => resolve(window.pywebview.api), { once: true }))
}

function swapAppearance(language, theme) {
  const override = document.createElement('style')
  override.textContent = '*,*::before,*::after{transition:none!important}'
  document.head.append(override)
  document.documentElement.lang = language
  document.documentElement.dir = language === 'fa' ? 'rtl' : 'ltr'
  document.documentElement.dataset.theme = theme
  void document.body.offsetHeight
  requestAnimationFrame(() => requestAnimationFrame(() => override.remove()))
}

function App() {
  const [api, setApi] = useState(null)
  const [ready, setReady] = useState(false)
  const [hasToken, setHasToken] = useState(false)
  const [preferences, setPreferences] = useState({ language: 'en', theme: 'system', onboarding_complete: false })
  const [systemDark, setSystemDark] = useState(window.matchMedia('(prefers-color-scheme: dark)').matches)
  const [view, setView] = useState('onboarding')
  const [onboardingStep, setOnboardingStep] = useState('language')
  const [settingsReturn, setSettingsReturn] = useState('teams')
  const [token, setToken] = useState('')
  const [tokenError, setTokenError] = useState('')
  const [teams, setTeams] = useState([])
  const [team, setTeam] = useState(null)
  const [folders, setFolders] = useState([])
  const [folder, setFolder] = useState(null)
  const [files, setFiles] = useState([])
  const [trail, setTrail] = useState([])
  const [authRequired, setAuthRequired] = useState(false)
  const [loginOpen, setLoginOpen] = useState(false)
  const [manual, setManual] = useState(false)
  const [teamInput, setTeamInput] = useState('')
  const [teamName, setTeamName] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [progress, setProgress] = useState(blankProgress)
  const language = preferences.language
  const t = (key, values) => translate(language, key, values)
  const appearance = preferences.theme === 'system' ? (systemDark ? 'dark' : 'light') : preferences.theme

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)')
    const update = () => setSystemDark(media.matches)
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  useEffect(() => { swapAppearance(language, appearance) }, [language, appearance])

  useEffect(() => {
    bridgeReady().then(async bridge => {
      setApi(bridge)
      try {
        const initial = await bridge.bootstrap()
        setHasToken(initial.has_token)
        setPreferences(initial.preferences)
        setTeams(initial.teams || [])
        setView(initial.preferences.onboarding_complete && initial.has_token ? 'teams' : 'onboarding')
        setOnboardingStep(initial.preferences.onboarding_complete ? 'token' : 'language')
        setReady(true)
        if (initial.preferences.onboarding_complete && initial.has_token) await discover(bridge)
      } catch (err) {
        setError(String(err).split('\n')[0])
        setReady(true)
      }
    })
  }, [])

  useEffect(() => {
    if (!api || view !== 'progress') return
    const timer = setInterval(async () => {
      try { setProgress(await api.status()) } catch (err) { setError(String(err).split('\n')[0]) }
    }, 800)
    return () => clearInterval(timer)
  }, [api, view])

  async function call(label, action) {
    setBusy(label); setError(''); setNotice('')
    try { return await action() }
    catch (err) { setError(String(err).split('\n')[0]); return null }
    finally { setBusy('') }
  }

  async function savePrefs(changes) {
    const result = await call('preferences', () => api.save_preferences(changes))
    if (result) setPreferences(result)
    return result
  }

  async function finishLanguage() {
    const result = await savePrefs({ language })
    if (!result) return
    if (!hasToken) { setOnboardingStep('token'); return }
    const completed = await savePrefs({ onboarding_complete: true })
    if (completed) { setView('teams'); await discover() }
  }

  async function saveToken(event) {
    event?.preventDefault()
    if (!token.trim()) { setTokenError(t('tokenRequired')); document.getElementById('access-token')?.focus(); return }
    setTokenError('')
    const result = await call('token', () => api.save_token(token))
    if (!result) return
    setToken(''); setHasToken(true)
    if (view === 'onboarding') {
      const completed = await savePrefs({ onboarding_complete: true })
      if (!completed) return
      setView('teams')
    } else {
      setNotice(t('tokenSavedNotice'))
    }
    await discover()
  }

  async function discover(bridge = api) {
    const result = await call('teams', () => bridge.discover_teams())
    if (!result) return
    setTeams(result.teams || [])
    setAuthRequired(!!result.auth_required)
    if (!result.auth_required) setLoginOpen(false)
  }

  async function signIn() {
    const result = await call('sign-in', () => api.open_sign_in())
    if (result) setLoginOpen(true)
  }

  async function addTeam(event) {
    event?.preventDefault()
    const result = await call('add-team', () => api.add_team(teamInput, teamName))
    if (!result) return
    setTeams(result.teams); setManual(false); setTeamInput(''); setTeamName('')
    await chooseTeam(result.team)
  }

  async function chooseTeam(value) {
    const result = await call('folders', () => api.folders(value.id))
    if (!result) return
    setTeam(value); setFolders(result.folders || []); setFolder(null); setFiles([]); setTrail([])
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

  async function startDownload(selection) {
    const result = await call('download', () => api.start_download({ team, ...selection }))
    if (!result) return
    setProgress({ ...blankProgress, running: true, phase: 'scanning', message: t('scanning') })
    setView('progress')
  }

  function openSettings() { setSettingsReturn(view); setView('settings'); setError(''); setNotice('') }
  function leaveSettings() { setView(settingsReturn); setToken(''); setTokenError(''); setError(''); setNotice('') }

  const done = progress.items.filter(item => ['saved', 'exists', 'renamed', 'skipped', 'failed'].includes(item.status)).length
  const percentage = progress.total ? Math.round(done / progress.total * 100) : 0
  const onboarding = view === 'onboarding'
  const title = onboarding ? (onboardingStep === 'language' ? t('languageTitle') : t('tokenTitle'))
    : view === 'settings' ? t('settingsTitle')
      : view === 'teams' ? t('teamsTitle')
        : view === 'browse' ? (folder?.name || team?.name || t('folderTitle'))
          : progress.running ? t('progressTitle') : progress.phase === 'done' ? (progress.failed ? t('progressPartial') : t('progressDone'))
            : progress.phase === 'stopped' ? t('progressStopped') : t('progressAttention')

  return <div class={'app-shell figma-' + appearance}>
    <a class="skip-link" href="#main">{t('browse')}</a>
    <header class="topbar">
      <div class="brand"><span class="brand-mark" aria-hidden="true">↓</span><span>Fig Backup</span></div>
      {!onboarding && <button class={'header-action ' + (view === 'settings' ? 'is-active' : '')} onClick={view === 'settings' ? leaveSettings : openSettings}>
        {view === 'settings' ? t('back') : t('settings')}
      </button>}
    </header>
    <main id="main" class={'main-panel ' + (onboarding ? 'onboarding-panel' : '')}>
      {!ready ? <div class="loading-view" role="status"><span class="spinner"></span>{t('loading')}</div> : <>
        <div class="page-heading">
          <div class="heading-copy">
            {onboarding && <div class="eyebrow">{t('onboardingEyebrow')}</div>}
            {view === 'browse' && <div class="breadcrumbs"><button onClick={() => setView('teams')}>{t('teamsTitle')}</button><span>/</span><button onClick={() => backTo(-1)}><bdi>{team?.name}</bdi></button>{trail.map((item, index) => <span class="crumb" key={item.id}><span>/</span><button onClick={() => backTo(index)}><bdi>{item.name}</bdi></button></span>)}</div>}
            <h1 tabIndex="-1">{title}</h1>
            <p>{onboarding ? (onboardingStep === 'language' ? t('languageDescription') : t('tokenDescription'))
              : view === 'settings' ? t('settingsDescription')
                : view === 'teams' ? t('teamsDescription')
                  : view === 'browse' ? t('folderDescription')
                    : progress.running ? t('largeFiles') : progress.destination}</p>
          </div>
          {view === 'teams' && <Button secondary onClick={() => discover()} disabled={!!busy} loading={busy === 'teams'}>{t('refresh')}</Button>}
          {view === 'browse' && <Button onClick={() => startDownload(folder ? { scope: 'folder', folder } : { scope: 'team' })} disabled={!!busy} loading={busy === 'download'}>{folder ? t('folderBackup') : t('teamBackup')}</Button>}
        </div>

        {error && <div class="message error" role="alert"><IconWarning16 /><span>{error} {t('errorPrefix')}</span><button onClick={() => setError('')} aria-label={t('close')}>×</button></div>}
        {notice && <div class="message notice" role="status"><span>{notice}</span><button onClick={() => setNotice('')} aria-label={t('close')}>×</button></div>}

        {onboarding && onboardingStep === 'language' && <section class="setup-card" aria-label={t('languageTitle')}>
          <div class="setup-step" dir="ltr">01 / 02</div>
          <div class="language-options">
            {[['en', 'English'], ['fa', 'فارسی']].map(([code, label]) =>
              <label class={'language-option ' + (language === code ? 'selected' : '')} key={code}>
                <input type="radio" name="setup-language" value={code} checked={language === code} onChange={() => setPreferences({ ...preferences, language: code })} />
                <span>{label}</span><span class="option-check">{language === code && <IconCheck16 />}</span>
              </label>)}
          </div>
          <div class="setup-actions"><Button onClick={finishLanguage} disabled={!!busy} loading={busy === 'preferences'}>{t('continue')}</Button></div>
        </section>}

        {onboarding && onboardingStep === 'token' && <section class="setup-card">
          <div class="setup-step" dir="ltr">02 / 02</div>
          <form onSubmit={saveToken} class="token-form">
            <label for="access-token">{t('tokenLabel')}</label>
            <Textbox id="access-token" password value={token} onValueInput={value => { setToken(value); setTokenError('') }} placeholder="figd_…" aria-invalid={!!tokenError} aria-describedby={tokenError ? 'token-error' : undefined} />
            {tokenError && <p id="token-error" class="field-error" role="alert">{tokenError}</p>}
            <p class="field-hint">{t('tokenHint')}</p>
            <p class="privacy-note">{t('tokenPrivacy')}</p>
            <div class="setup-actions"><Button secondary onClick={() => setOnboardingStep('language')}>{t('back')}</Button><Button onClick={saveToken} disabled={!!busy} loading={busy === 'token'}>{t('saveConnect')}</Button></div>
          </form>
        </section>}

        {view === 'settings' && <section class="settings-card">
          <div class="setting-row"><div><label for="setting-language">{t('language')}</label></div><select id="setting-language" value={language} onChange={async event => { const selected = event.currentTarget.value; if (await savePrefs({ language: selected })) setNotice(translate(selected, 'savedNotice')) }}><option value="en">English</option><option value="fa">فارسی</option></select></div>
          <div class="setting-row"><div><label for="setting-theme">{t('theme')}</label></div><select id="setting-theme" value={preferences.theme} onChange={async event => { if (await savePrefs({ theme: event.currentTarget.value })) setNotice(t('savedNotice')) }}><option value="system">{t('system')}</option><option value="light">{t('light')}</option><option value="dark">{t('dark')}</option></select></div>
          <div class="setting-row token-setting"><div><h2>{t('tokenSettings')}</h2><p>{hasToken ? t('tokenStored') : t('tokenMissing')}</p></div>
            <form onSubmit={saveToken} class="settings-token-form"><label for="access-token">{t('newToken')}</label><Textbox id="access-token" password value={token} onValueInput={value => { setToken(value); setTokenError('') }} placeholder="figd_…" aria-invalid={!!tokenError} aria-describedby={tokenError ? 'token-error' : undefined} />{tokenError && <p id="token-error" class="field-error" role="alert">{tokenError}</p>}<Button onClick={saveToken} disabled={!!busy} loading={busy === 'token'}>{t('replaceToken')}</Button></form>
          </div>
          <div class="settings-footnote">{t('privacyNote')}</div>
        </section>}

        {view === 'teams' && <section class="list-card">
          <div class="list-heading"><h2>{t('teamsTitle')}</h2><span>{t('teamCount', { count: teams.length })}</span></div>
          {authRequired && <div class="sign-in-banner"><div><strong>{t('signInTitle')}</strong><p>{t('signInDescription')}</p></div><Button onClick={loginOpen ? () => discover() : signIn} disabled={!!busy} loading={busy === 'sign-in' || busy === 'teams'}>{loginOpen ? t('signedIn') : t('openSignIn')}</Button></div>}
          <div class="entity-list">{teams.map(value => <button class="entity-row team-row" key={value.id} onClick={() => chooseTeam(value)} disabled={!!busy}><span class="entity-avatar">{value.name.slice(0, 1).toUpperCase()}</span><span class="entity-name"><bdi>{value.name}</bdi></span><span class="row-chevron" aria-hidden="true">›</span></button>)}</div>
          {!teams.length && <div class="empty-state">{t('noTeams')}</div>}
          {!manual ? <button class="link-action" onClick={() => setManual(true)}>{t('addTeam')}</button>
            : <form class="manual-form" onSubmit={addTeam}><label for="team-link">{t('teamLink')}</label><Textbox id="team-link" value={teamInput} onValueInput={setTeamInput} placeholder="https://www.figma.com/team/…" /><label for="team-name">{t('teamName')}</label><Textbox id="team-name" value={teamName} onValueInput={setTeamName} /><div class="form-actions"><Button secondary onClick={() => setManual(false)}>{t('cancel')}</Button><Button onClick={addTeam} disabled={!!busy}>{t('add')}</Button></div></form>}
        </section>}

        {view === 'browse' && <section class="list-card">
          <div class="list-heading"><h2>{t('folders')}</h2><span>{t('folderCount', { count: folders.length })}</span></div>
          <div class="entity-list">{folders.map(value => <div class="entity-row folder-row" key={value.id}><span class="entity-icon"><IconFolder16 /></span><span class="entity-name"><bdi>{value.name}</bdi></span><button class="row-action subtle" onClick={() => browseFolder(value)} disabled={!!busy} aria-label={t('open') + ' ' + value.name}>{t('open')}</button><button class="row-action" onClick={() => startDownload({ scope: 'folder', folder: value })} disabled={!!busy} aria-label={t('backup') + ' ' + value.name}>{t('backup')}</button></div>)}</div>
          {folder && <><div class="list-heading divided"><h2>{t('files')}</h2><span>{t('fileCount', { count: files.length })}</span></div><div class="entity-list">{files.map(value => <div class="entity-row file-row" key={value.key}><span class="entity-icon design"><IconDesign16 /></span><span class="entity-name"><bdi>{value.name}</bdi></span><button class="row-action" onClick={() => startDownload({ scope: 'file', folder, file_key: value.key })} disabled={!!busy} aria-label={t('downloadFile') + ' ' + value.name}>{t('downloadFile')}</button></div>)}</div></>}
          {!folders.length && !files.length && <div class="empty-state">{t('emptyFolder')}</div>}
          <div class="list-footnote">{t('downloadLocation')}</div>
        </section>}

        {view === 'progress' && <section class="list-card progress-card">
          <div class="progress-overview"><div><strong>{progress.total ? t('progressCount', { done, total: progress.total }) : t('scanning')}</strong><p>{progress.message}</p></div><span class="progress-number">{percentage}%</span></div>
          <div class="progress-track" role="progressbar" aria-valuenow={percentage} aria-valuemin="0" aria-valuemax="100" aria-label={t('progressTitle')}><div style={{ width: `${percentage}%` }} /></div>
          <div class="summary-strip"><span><b>{progress.saved}</b> {t('saved')}</span><span><b>{progress.existing}</b> {t('existing')}</span><span><b>{progress.skipped}</b> {t('skipped')}</span><span><b>{progress.failed}</b> {t('failed')}</span></div>
          {progress.warning && <div class="message notice">{progress.warning}</div>}
          <div class="queue-list">{progress.items.map((item, index) => <div class="queue-row" key={item.key}><span class="queue-index">{String(index + 1).padStart(2, '0')}</span><span class="queue-name"><bdi>{item.name}</bdi><small title={item.detail}>{item.detail}</small></span><span class={'status status-' + item.status}>{t(statusKeys[item.status] || item.status)}</span></div>)}</div>
          {!progress.running && !progress.items.length && <div class="empty-state">{t('queueEmpty')}</div>}
          <div class="progress-actions">{progress.running ? <Button secondary onClick={() => api.stop_download()}>{t('stop')}</Button> : <Button secondary onClick={() => setView(team ? 'browse' : 'teams')}>{t('browseAgain')}</Button>}<Button onClick={() => api.open_destination()}>{t('openDestination')}</Button></div>
        </section>}
      </>}
    </main>
    {!onboarding && <footer class="footer"><span>{t('downloadLocation')}</span><button onClick={() => api?.open_downloads()}>{t('downloads')} ↗</button></footer>}
  </div>
}

render(<App />, document.getElementById('app'))
