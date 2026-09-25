import test from 'node:test'
import assert from 'node:assert/strict'
import { queueProgressPercent, summarizeDownloadRun } from '../src/download-queue.js'

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
