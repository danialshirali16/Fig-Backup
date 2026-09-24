const firstLine = value => String(value || '').split('\n')[0].replace(/^Error:\s*/, '').trim()

export function downloadFailureDescription(status, queueName, translate) {
  const failedFiles = Array.isArray(status?.items)
    ? status.items.filter(item => item.status === 'failed')
    : []

  if (failedFiles.length > 0) {
    return failedFiles.map(file => {
      const name = firstLine(file.name)
      const reason = firstLine(file.detail) || translate('downloadFailureFallback')
      return name && name !== queueName ? `${name}: ${reason}` : reason
    }).join('\n')
  }

  if (status?.phase === 'error') {
    return firstLine(status.message) || translate('downloadFailureFallback')
  }

  return translate('downloadFailureFallback')
}
