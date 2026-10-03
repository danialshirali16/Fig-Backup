/* Keep the bridge work and navigation in one operation so Retry completes the
   same transition, including closing a visible sign-in window if needed. */
export async function openSetupStep({ api, step, view, loginOpen, onReset, onLoginClosed, onOpen }) {
  if (step === 'browser' && view !== 'wizard') {
    const reset = await api.begin_setup()
    onReset(reset.preferences)
  }
  if (loginOpen && step !== 'signin') {
    await api.close_sign_in()
    onLoginClosed()
  }
  onOpen(step)
}
