import test from 'node:test'
import assert from 'node:assert/strict'
import { downloadFailureDescription } from '../src/download-errors.js'

const translate = () => 'Download failed. Try again.'

test('shows failed file reasons instead of the last progress filename', () => {
  const status = {
    phase: 'done', message: 'Last processed file',
    items: [
      { name: 'One', status: 'saved', detail: '/Downloads/One.fig' },
      { name: 'Zhina on Live', status: 'failed', detail: 'Figma returned HTTP 403' },
    ],
  }
  assert.equal(downloadFailureDescription(status, 'Live', translate), 'Zhina on Live: Figma returned HTTP 403')
})

test('lists each failed file and falls back when a reason is missing', () => {
  const status = {
    phase: 'done',
    items: [
      { name: 'A', status: 'failed', detail: 'Network timeout\ntraceback' },
      { name: 'B', status: 'failed', detail: '' },
    ],
  }
  assert.equal(downloadFailureDescription(status, 'Folder', translate), 'A: Network timeout\nB: Download failed. Try again.')
})

test('uses top-level errors and never uses progress text as a failure reason', () => {
  assert.equal(downloadFailureDescription({ phase: 'error', message: 'Error: Folder is unavailable' }, 'Folder', translate), 'Folder is unavailable')
  assert.equal(downloadFailureDescription({ phase: 'done', message: 'Last processed file' }, 'Folder', translate), 'Download failed. Try again.')
})
