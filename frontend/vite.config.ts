import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/static/', // Prefix built asset URLs with /static/ for FastAPI routing compatibility
  build: {
    outDir: '../static',
    emptyOutDir: false, // Keep other assets in the static folder (avatars, logos)
    rollupOptions: {
      input: {
        landingpage: 'landingpage.html',
        login: 'login.html',
        chat: 'chat.html',
        onboarding: 'onboarding.html',
      }
    }
  }
})
