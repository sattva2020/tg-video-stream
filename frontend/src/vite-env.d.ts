/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_API_URL: string
  // Telegram Login Widget
  readonly VITE_TELEGRAM_BOT_USERNAME: string
  // Cloudflare Turnstile CAPTCHA
  readonly VITE_TURNSTILE_SITE_KEY: string
  readonly VITE_DEFAULT_THEME?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
