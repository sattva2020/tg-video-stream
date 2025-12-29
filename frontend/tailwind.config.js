/** @type {import('tailwindcss').Config} */
import { heroui } from "@heroui/react";

export default {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./node_modules/@heroui/**/dist/**/*.{js,mjs}",
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
      animation: {
        'gradient-x': 'gradient-x 3s ease infinite',
        'spin-slow': 'spin 2s linear infinite',
        'spin-very-slow': 'spin 120s linear infinite',
        'pulse-slow': 'pulse-slow 4s ease-in-out infinite',
        'glow': 'glow 3s ease-in-out infinite',
        'float': 'float 6s ease-in-out infinite',
        'twinkle': 'twinkle 3s ease-in-out infinite',
        'drift': 'drift 60s linear infinite',
        'clouds': 'clouds 90s linear infinite',
        'orbit': 'orbit 30s linear infinite',
        'orbit-reverse': 'orbit 45s linear infinite reverse',
      },
      keyframes: {
        'gradient-x': {
          '0%, 100%': {
            'background-size': '200% 200%',
            'background-position': 'left center',
          },
          '50%': {
            'background-size': '200% 200%',
            'background-position': 'right center',
          },
        },
        'pulse-slow': {
          '0%, 100%': {
            opacity: '0.5',
            transform: 'scale(1)',
          },
          '50%': {
            opacity: '0.8',
            transform: 'scale(1.02)',
          },
        },
        'glow': {
          '0%, 100%': {
            opacity: '0.3',
            transform: 'scale(0.95)',
          },
          '50%': {
            opacity: '0.7',
            transform: 'scale(1.1)',
          },
        },
        'float': {
          '0%, 100%': {
            transform: 'translateY(0)',
          },
          '50%': {
            transform: 'translateY(-10px)',
          },
        },
        'twinkle': {
          '0%, 100%': {
            opacity: '0.3',
            transform: 'scale(1)',
          },
          '50%': {
            opacity: '1',
            transform: 'scale(1.2)',
          },
        },
        'drift': {
          '0%': {
            transform: 'translateX(0) rotate(0deg)',
          },
          '100%': {
            transform: 'translateX(-20px) rotate(5deg)',
          },
        },
        'clouds': {
          '0%': {
            transform: 'translateX(0)',
          },
          '100%': {
            transform: 'translateX(30px)',
          },
        },
        'orbit': {
          '0%': {
            transform: 'rotateX(75deg) rotateZ(0deg)',
          },
          '100%': {
            transform: 'rotateX(75deg) rotateZ(360deg)',
          },
        },
      },
    },
  },
  plugins: [heroui()],
}