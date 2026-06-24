/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#0f1117',
        card: '#1a1d2e',
        border: '#2a2d3e',
        accent: '#3b82f6',
        green: { DEFAULT: '#22c55e', dim: '#166534' },
        red: { DEFAULT: '#ef4444', dim: '#7f1d1d' },
        amber: { DEFAULT: '#f59e0b', dim: '#78350f' },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
}
