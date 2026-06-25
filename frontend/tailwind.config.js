/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        surface:   '#0a0a0f',
        'surface-low': '#0f1018',
        'surface-mid': '#13162a',
        'surface-high': '#1a1d2e',
        // Glass
        'glass-bg':     'rgba(255, 255, 255, 0.06)',
        'glass-border': 'rgba(255, 255, 255, 0.10)',
        // Brand / primary accent
        brand:     '#e85d04',
        'brand-dim': '#7a3102',
        // Status colors
        teal:       '#41eec2',
        'teal-dim': '#1a5c4a',
        // Semantic
        positive:   '#22c55e',
        negative:   '#ef4444',
        warning:    '#f59e0b',
        // Text
        'text-primary':   '#f5f5f5',
        'text-secondary': '#d0d0de',
        'text-dim':       '#b0b0c4',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
      backdropBlur: {
        glass: '16px',
      },
    },
  },
  plugins: [],
}
