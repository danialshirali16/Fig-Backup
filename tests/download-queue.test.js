import test from 'node:test'
import assert from 'node:assert/strict'
import { queueProgressPercent, runOutcome, summarizeDownloadRun } from '../src/download-queue.js'

const translate = (key, values) => ({
  queueEmpty: 'No supported files were found.',
  skipped: 'Unsupported file type',
  progressCount: `${values?.done} of ${values?.total} files`,
  progressCountOne: `${values?.done} of ${values?.total} file`,
  downloadFailureFallback: 'Download failed.',
})[key]

test('all skipped files leave the queue item skipped and progress at zero', () => {
  const run = {
    phase: 'done', total: 2, skipped: 2, failed: 0,
    items: [{ status: 'skipped' }, { status: 'skipped' }],
  }
  const item = summarizeDownloadRun(run, 'Folder', translate)
  assert.equal(item.status, 'skipped')
  assert.equal(item.detail, 'No supported files were found.')
  assert.equal(item.filesDone, 0)
  assert.equal(queueProgressPercent([item], run), 0)
})

test('mixed results count saved files and leave skipped files incomplete', () => {
  const run = {
    phase: 'done', total: 2, skipped: 1, failed: 0,
    items: [{ status: 'saved', size: 2048 }, { status: 'skipped' }],
  }
  const item = summarizeDownloadRun(run, 'Folder', translate)
  assert.equal(item.status, 'partial')
  assert.equal(item.detail, '1 of 2 files · Unsupported file type')
  assert.equal(item.bytes, 2048)
  assert.equal(queueProgressPercent([item, { status: 'queued' }], run), 25)
})

test('successful and live runs count only saved or existing files', () => {
  const run = {
    phase: 'done', total: 2, skipped: 0, failed: 0,
    items: [{ status: 'saved' }, { status: 'exists' }],
  }
  assert.equal(summarizeDownloadRun(run, 'Folder', translate).status, 'done')
  assert.equal(queueProgressPercent([{ status: 'done' }], run), 100)
  assert.equal(queueProgressPercent([{ status: 'running' }], {
    running: true, total: 3,
    items: [{ status: 'saved' }, { status: 'skipped' }, { status: 'queued' }],
  }), 33)
})

test('a skipped file cannot round incomplete progress up to 100 percent', () => {
  const item = { status: 'partial', filesDone: 999, filesTotal: 1000 }
  assert.equal(queueProgressPercent([item], null), 99)
})

test('an empty selection reports no supported files instead of zero files', () => {
  const run = { phase: 'done', total: 0, skipped: 0, failed: 0, items: [] }
  const item = summarizeDownloadRun(run, 'Folder', translate)
  assert.equal(item.status, 'done')
  assert.equal(item.detail, 'No supported files were found.')
  assert.equal(item.filesDone, 0)
})

/* The row caption claims what the run did, so a file that was already on disk
   must not be reported as freshly saved. */
test('a run where every file already existed reports the exists outcome', () => {
  const run = {
    phase: 'done', total: 2, skipped: 0, failed: 0,
    items: [{ status: 'exists', key: 'a' }, { status: 'exists', key: 'b' }],
  }
  const item = summarizeDownloadRun(run, 'Folder', translate)
  assert.equal(item.outcome, 'exists')
  assert.equal(item.filesDone, 2)
  assert.equal(item.bytes, 0, 'an existing file reports no size, so no byte count is shown')
})

test('a run that only migrated legacy names reports the renamed outcome', () => {
  const run = {
    phase: 'done', total: 1, skipped: 0, failed: 0,
    items: [{ status: 'renamed', key: 'a' }],
  }
  assert.equal(summarizeDownloadRun(run, 'File', translate).outcome, 'renamed')
})

test('one new copy in the run makes the whole run a saved outcome', () => {
  const run = {
    phase: 'done', total: 3, skipped: 0, failed: 0,
    items: [{ status: 'exists', key: 'a' }, { status: 'saved', key: 'b', size: 2048 }, { status: 'exists', key: 'c' }],
  }
  const item = summarizeDownloadRun(run, 'Folder', translate)
  assert.equal(item.outcome, 'saved')
  assert.equal(item.bytes, 2048)
})

test('a run with nothing finished has no outcome to report', () => {
  assert.equal(runOutcome([]), 'none')
  assert.equal(summarizeDownloadRun({ phase: 'done', total: 0, items: [] }, 'Folder', translate).outcome, 'none')
})

test('a skip keeps the reason the file gave instead of the generic label', () => {
  // A run cancelled on a name clash is skipped, not "unsupported file type" —
  // the generic wording would blame the user's file for their own decision.
  const run = {
    phase: 'done', total: 1, skipped: 0, failed: 0,
    items: [{ status: 'skipped', detail: 'Skipped — a file with this name already existed' }],
  }
  const item = summarizeDownloadRun(run, 'Folder', translate)
  assert.equal(item.status, 'skipped')
  assert.match(item.detail, /already existed/)
})

test('an unsupported file still falls back to the generic reason', () => {
  const run = { phase: 'done', total: 1, items: [{ status: 'skipped', detail: 'File type: library' }] }
  assert.equal(summarizeDownloadRun(run, 'Folder', translate).status, 'skipped')
})

test('a conflict skip is reported as a code the UI can translate', () => {
  const run = {
    phase: 'done', total: 1, skipped: 0, failed: 0,
    items: [{ status: 'skipped', detail: 'conflict' }],
  }
  assert.equal(summarizeDownloadRun(run, 'Folder', translate).status, 'skipped')
  // English prose here would reach a Persian or Japanese user untranslated.
  assert.equal(summarizeDownloadRun(run, 'Folder', translate).detail, 'conflict')
})
