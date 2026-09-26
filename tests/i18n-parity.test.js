import test from 'node:test'
import assert from 'node:assert/strict'
import { copy, LANGUAGES, RTL_LANGUAGES, translate } from '../src/i18n.js'

/* Every locale must carry exactly the English key set. A missing key renders the raw
   key at runtime; a stray key is dead weight shipped to every user. */
const ENGLISH = Object.keys(copy.en).sort()
const placeholders = value => (String(value).match(/\{(\w+)\}/g) || []).sort()

test('every locale has exactly the English key set', () => {
  for (const language of LANGUAGES) {
    const keys = Object.keys(copy[language.code] || {}).sort()
    const missing = ENGLISH.filter(key => !keys.includes(key))
    const extra = keys.filter(key => !ENGLISH.includes(key))
    assert.deepEqual(missing, [], `${language.code} is missing keys`)
    assert.deepEqual(extra, [], `${language.code} has keys English does not`)
  }
})

test('every locale declares the language it is registered under', () => {
  for (const language of LANGUAGES) {
    assert.ok(copy[language.code], `no copy for ${language.code}`)
    assert.equal(typeof language.native, 'string')
    assert.ok(language.native.length > 0, `${language.code} has no native name`)
  }
})

test('translations keep the placeholders of the English string', () => {
  for (const language of LANGUAGES) {
    if (language.code === 'en') continue
    for (const key of ENGLISH) {
      assert.deepEqual(
        placeholders(copy[language.code][key]),
        placeholders(copy.en[key]),
        `${language.code}.${key} placeholders differ from English`,
      )
    }
  }
})

test('no translation is blank', () => {
  for (const language of LANGUAGES) {
    for (const key of ENGLISH) {
      const value = copy[language.code][key]
      assert.equal(typeof value, 'string', `${language.code}.${key} is not a string`)
      assert.ok(value.trim().length > 0, `${language.code}.${key} is empty`)
    }
  }
})

test('a missing key falls back to English rather than rendering the key', () => {
  assert.equal(translate('fa', 'sectionNeedsAttention'), copy.fa.sectionNeedsAttention)
  assert.equal(translate('fa', 'noSuchKeyAnywhere'), 'noSuchKeyAnywhere')
  assert.equal(translate('xx', 'done'), copy.en.done)
})

test('interpolates values and blanks any placeholder it was not given', () => {
  assert.equal(translate('en', 'ofSelected', { count: 3, total: 12 }), '3 of 12 selected')
  assert.equal(translate('en', 'ofSelected', { count: 3 }), '3 of  selected')
})

test('RTL_LANGUAGES matches the rtl flags on LANGUAGES', () => {
  for (const language of LANGUAGES) {
    assert.equal(RTL_LANGUAGES.has(language.code), Boolean(language.rtl), language.code)
  }
})
