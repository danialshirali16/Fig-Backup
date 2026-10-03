import test from 'node:test'
import assert from 'node:assert/strict'
import { toggleVisibleSelection, visibleSelectionState } from '../src/selection.js'

test('select-all after a search selects only matching folders and files', () => {
  const parent = { id: 'parent', name: 'Project' }
  const folders = [{ id: 'a', name: 'Match folder' }, { id: 'hidden', name: 'Unrelated' }]
  const files = [{ key: 'b', name: 'Match file', editorType: 'slides' }, { key: 'hidden', name: 'Unrelated' }]
  const visibleFolders = folders.filter(folder => folder.name.includes('Match'))
  const visibleFiles = files.filter(file => file.name.includes('Match'))
  const selection = { folders: [], files: [] }
  const selected = toggleVisibleSelection(selection, visibleFolders, visibleFiles, parent)
  assert.deepEqual(selected.folders, [folders[0]])
  assert.deepEqual(selected.files, [{ ...files[0], folder: parent }])
  assert.deepEqual(visibleSelectionState(selected, visibleFolders, visibleFiles), {
    selected: 2, total: 2, checked: true,
  })
  assert.deepEqual(selection, { folders: [], files: [] }, 'selection updates preserve the previous state')
})

test('visible checkbox and counter ignore selected rows outside the search results', () => {
  const visibleFolders = [{ id: 'a' }]
  const visibleFiles = [{ key: 'b' }]
  const hidden = { id: 'hidden' }
  const elsewhere = { key: 'elsewhere', folder: { id: 'another-folder' } }
  const selection = { folders: [visibleFolders[0], hidden], files: [elsewhere] }
  assert.deepEqual(visibleSelectionState(selection, visibleFolders, visibleFiles), {
    selected: 1, total: 2, checked: 'indeterminate',
  })
  const selected = toggleVisibleSelection(selection, visibleFolders, visibleFiles, { id: 'parent' })
  assert.equal(visibleSelectionState(selected, visibleFolders, visibleFiles).checked, true)
  const deselected = toggleVisibleSelection(selected, visibleFolders, visibleFiles, { id: 'parent' })
  assert.deepEqual(deselected, { folders: [hidden], files: [elsewhere] })
})

test('an empty search has no checked state and leaves existing selections intact', () => {
  const selection = { folders: [{ id: 'hidden' }], files: [{ key: 'elsewhere' }] }
  assert.deepEqual(visibleSelectionState(selection, [], []), { selected: 0, total: 0, checked: false })
  assert.deepEqual(toggleVisibleSelection(selection, [], [], null), selection)
})
