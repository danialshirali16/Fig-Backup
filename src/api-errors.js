/* Turns a backend error message into something a person can act on.
   Pure on purpose: no React, no i18n import, so it is testable on its own.

   The backend keeps its messages short and stable on purpose (see
   FigmaClient.get and Browser._goto) so they can be classified here without
   matching library internals. */

/* The wrapped messages are the normal path, but these patterns also recognise
   raw urllib3 / Playwright text. That is deliberate: if some future path leaks
   an unwrapped message, the user still gets "check your connection" instead of
   a wall of library internals. */
const NETWORK = /could not reach figma|took too long to respond|max retries exceeded|read timed out|timed out|connection (?:refused|reset|aborted|failed)|newconnectionerror|nodename nor servname|name or service not known|\bdns\b|net::err_(?:name_not_resolved|connection_refused|internet_disconnected|network_changed|address_unreachable|connection_reset)|offline/i
const RATE = /figma is busy|http 429|too many requests|rate.?limit/i
const ACCESS = /refused the request|http 40[13]|invalid token|forbidden|not authorized|permission|missing scope|api key/i

export function classifyApiError(message) {
  const text = String(message || '')
  if (NETWORK.test(text)) return 'network'
  if (RATE.test(text)) return 'rate'
  if (ACCESS.test(text)) return 'access'
  return 'unknown'
}

/* `title` is the headline, `hint` the thing to do about it, and `detail` the raw
   backend line — kept only when it says something the title does not, so the
   user has something concrete to paste into a bug report. */
export function describeApiError(message, t) {
  const raw = String(message || '').trim()
  const kind = classifyApiError(raw)
  if (kind === 'network') return { kind, title: t('errorNetwork'), hint: t('errorPrefix'), detail: raw }
  if (kind === 'rate') return { kind, title: t('errorRate'), hint: t('rateRecovery'), detail: raw }
  if (kind === 'access') {
    // A 401 is a token problem, not a team-permission one; say the right thing.
    const token = /http 401|invalid token/i.test(raw)
    return {
      kind,
      title: t(token ? 'errorToken' : 'errorAccess'),
      hint: t(token ? 'tokenRecovery' : 'accessRecovery'),
      detail: raw,
    }
  }
  return { kind, title: raw, hint: t('errorPrefix'), detail: '' }
}
