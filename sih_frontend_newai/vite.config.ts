import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  if (command === 'build') {
    const value = env.VITE_API_BASE_URL?.trim()
    let url: URL
    try { url = new URL(value || '') }
    catch { throw new Error('Set VITE_API_BASE_URL to the deployed HTTPS backend URL before building.') }
    if (url.protocol !== 'https:' || /^(localhost|127\..*|\[::1\])$/i.test(url.hostname) || url.username || url.password || url.search || url.hash) {
      throw new Error('VITE_API_BASE_URL must be a public HTTPS backend base URL without credentials, query, or fragment.')
    }
  }
  return { plugins: [react()] }
})
