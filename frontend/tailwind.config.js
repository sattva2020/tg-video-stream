/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      screens: {
        xs: '320px',
        '3xl': '1920px',
        '4xl': '2560px',
      },
      maxWidth: {
        landing: '80rem',
        'landing-wide': '96rem',
        'landing-ultra': '108rem',
      },
      colors: {
        parchment: 'var(--color-surface)',
        'parchment-muted': 'var(--color-surface-muted)',
        ink: 'var(--color-text)',
        'ink-muted': 'var(--color-text-muted)',
        accent: 'var(--color-accent)',
        night: 'var(--color-night-sky)',
      },
      backgroundImage: {
        'brand-glow': 'linear-gradient(135deg, #38bdf8 0%, #0ea5e9 45%, #0f172a 100%)',
      },
      blur: {
        'landing-md': '120px',
        'landing-lg': '240px',
      },
      spacing: {
        base: 'var(--space-base)',
      },
      transitionDuration: {
        theme: 'var(--transition-theme-duration)',
      },
      transitionTimingFunction: {
        theme: 'var(--transition-theme-easing)',
      },
      fontFamily: {
        cinzel: ['Cinzel', 'serif'],
        lato: ['Lato', 'sans-serif'],
        heading: ['var(--font-heading)', 'serif'],
        body: ['var(--font-body)', 'sans-serif'],
        'landing-sans': ['var(--landing-font-sans)', 'sans-serif'],
        'landing-serif': ['var(--landing-font-serif)', 'serif'],
      },
    },
  },
  plugins: [],
}