/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Premium dark base
        dark: {
          base: '#0d1117',
          surface: '#111827',
          elevated: '#0f172a',
          card: '#1e293b',
        },
        // Neon accents
        neon: {
          green: '#4ade80',
          cyan: '#60a5fa',
          blue: '#38bdf8',
        },
        // Status colors
        status: {
          success: '#4ade80',
          warning: '#fbbf24',
          error: '#ef4444',
          info: '#60a5fa',
        },
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#60a5fa',
          600: '#3b82f6',
          700: '#2563eb',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
      boxShadow: {
        'soft': '0 2px 8px rgba(0, 0, 0, 0.15)',
        'card': '0 4px 12px rgba(0, 0, 0, 0.25)',
        'glow-green': '0 0 20px rgba(74, 222, 128, 0.3)',
        'glow-cyan': '0 0 20px rgba(96, 165, 250, 0.3)',
        'glow-blue': '0 0 20px rgba(56, 189, 248, 0.3)',
      },
      borderRadius: {
        'card': '12px',
        'button': '8px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
}
