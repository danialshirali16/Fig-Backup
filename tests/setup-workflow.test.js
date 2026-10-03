import test from 'node:test'
import assert from 'node:assert/strict'
import { openSetupStep } from '../src/setup-workflow.js'

function workflowOptions(state, api, step = 'browser') {
  return {
    api, step, view: state.view, loginOpen: state.loginOpen,
    onReset: preferences => { state.preferences = preferences; state.verifiedName = '' },
    onLoginClosed: () => { state.loginOpen = false },
    onOpen: nextStep => { state.step = nextStep; state.view = 'wizard' },
  }
}

test('retrying a failed setup reset also opens the browser setup step', async () => {
  const state = { view: 'settings', step: 'signin', loginOpen: false, verifiedName: 'User' }
  let calls = 0
  const api = {
    begin_setup: async () => {
      if (++calls === 1) throw new Error('temporary bridge failure')
      return { preferences: { onboarding_complete: false } }
    },
  }
  const options = workflowOptions(state, api)
  const operation = () => openSetupStep(options)
  await assert.rejects(operation(), /temporary bridge failure/)
  assert.equal(state.view, 'settings')
  await operation()
  assert.equal(calls, 2)
  assert.deepEqual(state, {
    view: 'wizard', step: 'browser', loginOpen: false, verifiedName: '',
    preferences: { onboarding_complete: false },
  })
})

test('retrying a failed sign-in close updates the window state and changes the step', async () => {
  const state = { view: 'wizard', step: 'signin', loginOpen: true }
  let calls = 0
  const api = {
    close_sign_in: async () => {
      if (++calls === 1) throw new Error('could not close yet')
    },
  }
  const options = workflowOptions(state, api, 'token')
  const operation = () => openSetupStep(options)
  await assert.rejects(operation(), /could not close yet/)
  assert.deepEqual(state, { view: 'wizard', step: 'signin', loginOpen: true })
  await operation()
  assert.equal(calls, 2)
  assert.deepEqual(state, { view: 'wizard', step: 'token', loginOpen: false })
})

test('a retry after reset succeeds but sign-in close fails completes the whole transition', async () => {
  const state = { view: 'settings', step: 'signin', loginOpen: true }
  const events = []
  let closeCalls = 0
  const api = {
    begin_setup: async () => { events.push('reset'); return { preferences: { onboarding_complete: false } } },
    close_sign_in: async () => {
      events.push('close')
      if (++closeCalls === 1) throw new Error('close interrupted')
    },
  }
  const options = workflowOptions(state, api)
  const operation = () => openSetupStep(options)
  await assert.rejects(operation(), /close interrupted/)
  assert.equal(state.view, 'settings')
  assert.equal(state.loginOpen, true)
  await operation()
  assert.deepEqual(events, ['reset', 'close', 'reset', 'close'])
  assert.equal(state.loginOpen, false)
  assert.equal(state.view, 'wizard')
  assert.equal(state.step, 'browser')
})

test('returning to the sign-in step keeps its open window without repeating setup', async () => {
  const state = { view: 'settings', step: 'token', loginOpen: true }
  await openSetupStep(workflowOptions(state, {}, 'signin'))
  assert.deepEqual(state, { view: 'wizard', step: 'signin', loginOpen: true })
})
