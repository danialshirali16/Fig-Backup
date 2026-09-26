import { downloadFailureDescription } from './download-errors.js'

export const DONE_STATES = ['saved', 'exists', 'renamed']

/* What a finished run actually did, so a row caption never claims work that did
   not happen: 'exists' when every file was already on disk, 'renamed' when only
   a legacy name was migrated, 'saved' when at least one new copy was written. */
export function runOutcome(doneFiles) {
  if (!doneFiles.length) return 'none'
  if (doneFiles.some(file => file.status === 'saved')) return 'saved'
  return doneFiles.every(file => file.status === 'renamed') ? 'renamed' : 'exists'
}

export function summarizeDownloadRun(status, queueName, translate) {
  const files = Array.isArray(status?.items) ? status.items : []
  const doneFiles = files.filter(file => DONE_STATES.includes(file.status))
  const skipped = files.filter(file => file.status === 'skipped').length
  const filesTotal = Math.max(status?.total || 0, files.length)
  const failed = status?.phase === 'error' || status?.failed > 0
  const runStatus = status?.phase === 'stopped' ? 'stopped' : failed ? 'failed' : skipped ? (doneFiles.length ? 'partial' : 'skipped') : 'done'
  const skippedDetail = doneFiles.length
    ? `${translate(filesTotal === 1 ? 'progressCountOne' : 'progressCount', { done: doneFiles.length, total: filesTotal })} · ${translate('skipped')}`
    : translate('queueEmpty')

  return {
    status: runStatus,
    detail: failed
      ? downloadFailureDescription(status, queueName, translate)
      : skipped
        ? skippedDetail
        : filesTotal === 0 ? translate('queueEmpty') : '',
    bytes: doneFiles.reduce((sum, file) => sum + (file.size || 0), 0),
    filesDone: doneFiles.length,
    filesTotal,
    outcome: runOutcome(doneFiles),
  }
}

export function queueProgressPercent(queue, liveStatus) {
  if (!queue.length) return 0
  const liveDone = Array.isArray(liveStatus?.items)
    ? liveStatus.items.filter(file => DONE_STATES.includes(file.status)).length
    : 0
  const completed = queue.reduce((sum, item) => {
    if (item.status === 'done') return sum + 1
    if (item.status === 'running') {
      return sum + (liveStatus?.running && liveStatus.total > 0 ? Math.min(liveDone, liveStatus.total) / liveStatus.total : 0)
    }
    if (item.status === 'partial' || item.status === 'skipped' || item.status === 'failed' || item.status === 'stopped') {
      return sum + (item.filesTotal > 0 ? Math.min(item.filesDone || 0, item.filesTotal) / item.filesTotal : 0)
    }
    return sum
  }, 0)
  return Math.floor(completed / queue.length * 100)
}
