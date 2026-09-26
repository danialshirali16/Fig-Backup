import test from 'node:test'
import assert from 'node:assert/strict'
import { classifyApiError, describeApiError } from '../src/api-errors.js'

const t = key => `<${key}>`

test('a dropped connection is reported as a network problem', () => {
  assert.equal(classifyApiError('Could not reach Figma: ConnectionError.'), 'network')
  assert.equal(classifyApiError('Figma took too long to respond: https://www.figma.com/files'), 'network')
})

test('a raw library message is still recognised as a network problem', () => {
  // Before this module existed these fell through to the generic "try again"
  // copy, which is the wrong advice precisely when the connection is the cause.
  const raw = "HTTPSConnectionPool(host='api.figma.com', port=443): Max retries exceeded with url: /v1/me (Caused by NameResolutionError('<urlopen error [Errno 8] nodename nor servname provided>'))"
  assert.equal(classifyApiError(raw), 'network')
  assert.equal(classifyApiError("HTTPSConnectionPool(host='api.figma.com', port=443): Read timed out. (read timeout=30)"), 'network')
})

test('an HTTP refusal is an access problem, and a 401 is a token problem', () => {
  const forbidden = describeApiError('Figma refused the request (HTTP 403): Not authorized.', t)
  assert.equal(forbidden.kind, 'access')
  assert.equal(forbidden.title, '<errorAccess>')
  assert.equal(forbidden.hint, '<accessRecovery>')

  const badToken = describeApiError('Figma refused the request (HTTP 401): Invalid token', t)
  assert.equal(badToken.kind, 'access')
  assert.equal(badToken.title, '<errorToken>')
  assert.equal(badToken.hint, '<tokenRecovery>')
})

test('rate limiting gets its own title and advice', () => {
  const busy = describeApiError('Figma is busy (HTTP 429).', t)
  assert.equal(busy.kind, 'rate')
  assert.equal(busy.title, '<errorRate>')
  assert.equal(busy.hint, '<rateRecovery>')
})

test('network is checked before access so a timeout is not blamed on permissions', () => {
  // "took too long" must not fall into the access bucket just because a URL
  // in the message happens to contain a path segment.
  assert.equal(classifyApiError('Figma took too long to respond: https://www.figma.com/design/abc'), 'network')
})

test('a file name that merely mentions sign-in is not an error at all', () => {
  // The run message after a finished backup is the last file's NAME. Treating
  // "Sign-in redesign" as a session failure wiped a completed setup.
  assert.equal(classifyApiError('Sign-in redesign'), 'unknown')
  assert.equal(classifyApiError('Re-sign in flow mockups'), 'unknown')
  assert.equal(describeApiError('Sign-in redesign', t).title, 'Sign-in redesign')
})

test('an unrecognised message is shown as-is with no redundant detail block', () => {
  const unknown = describeApiError('Choose a valid team', t)
  assert.equal(unknown.kind, 'unknown')
  assert.equal(unknown.title, 'Choose a valid team')
  assert.equal(unknown.detail, '', 'the detail block must not repeat the title')
})

test('a classified message keeps its raw text so a bug report has something concrete', () => {
  const raw = 'Figma refused the request (HTTP 403): Not authorized.'
  assert.equal(describeApiError(raw, t).detail, raw)
})

test('an empty message does not throw', () => {
  assert.equal(classifyApiError(''), 'unknown')
  assert.equal(classifyApiError(undefined), 'unknown')
  assert.equal(describeApiError(null, t).title, '')
})

test('raw Chromium and Playwright network text is recognised too', () => {
  // browser.py wraps these, but the safety net should not depend on that.
  for (const raw of [
    'net::ERR_NAME_NOT_RESOLVED at https://www.figma.com/files',
    'net::ERR_INTERNET_DISCONNECTED',
    'Error: net::ERR_CONNECTION_REFUSED',
  ]) {
    assert.equal(classifyApiError(raw), 'network', raw)
  }
})

test('a normal 403 is not mistaken for a connection problem', () => {
  // "refused the request" and "connection refused" are easy to confuse.
  assert.equal(classifyApiError('Figma refused the request (HTTP 403): Not authorized.'), 'access')
  assert.equal(classifyApiError('Figma is busy (HTTP 429).'), 'rate')
})
