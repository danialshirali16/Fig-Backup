/* Both the select-all control and its count describe the filtered rows on screen.
   The team-wide selection still keeps items selected in other views. */
export function visibleSelectionState(selection, folders, files) {
  const folderIds = new Set(selection.folders.map(folder => folder.id))
  const fileKeys = new Set(selection.files.map(file => file.key))
  const total = folders.length + files.length
  const selected = folders.filter(folder => folderIds.has(folder.id)).length
    + files.filter(file => fileKeys.has(file.key)).length
  return {
    selected,
    total,
    checked: total > 0 && selected === total ? true : selected > 0 ? 'indeterminate' : false,
  }
}

export function toggleVisibleSelection(selection, folders, files, parentFolder) {
  const folderIds = new Set(folders.map(folder => folder.id))
  const fileKeys = new Set(files.map(file => file.key))
  const remaining = {
    folders: selection.folders.filter(folder => !folderIds.has(folder.id)),
    files: selection.files.filter(file => !fileKeys.has(file.key)),
  }
  if (visibleSelectionState(selection, folders, files).checked === true) return remaining
  return {
    folders: [...remaining.folders, ...folders],
    files: [...remaining.files, ...files.map(file => ({
      key: file.key, name: file.name, folder: parentFolder, editorType: file.editorType,
    }))],
  }
}
