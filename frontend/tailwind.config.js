/** @type {import('tailwindcss').Config} */
export default {
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
        parchment: '#f3e9d2',
        ink: '#4a3b32',
        gold: '#c5a059',
        'brand-sky': '#0ea5e9',
        'brand-glow': '#38bdf8',
        'brand-midnight': '#0f172a',
        'brand-graphite': '#1f2937',
      },
      backgroundImage: {
        'brand-glow': 'linear-gradient(135deg, #38bdf8 0%, #0ea5e9 45%, #0f172a 100%)',
      },
      blur: {
        'landing-md': '120px',
        'landing-lg': '240px',
      },
      fontFamily: {
        cinzel: ['Cinzel', 'serif'],
        lato: ['Lato', 'sans-serif'],
      },
    },
  },
  plugins: [],
}