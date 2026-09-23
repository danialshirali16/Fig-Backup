import { createRoot } from 'react-dom/client'
import App from './App'
import './index.css'
import { installPreviewBridge } from './preview-bridge'

if (import.meta.env.DEV && new URLSearchParams(window.location.search).has('preview')) {
  installPreviewBridge()
}

createRoot(document.getElementById('app')).render(<App />)
