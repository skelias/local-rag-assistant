/** @type {import('tailwindcss').Config} */
// DSH 桌面风配色（skin-map-dsh-final.md），2026-09-09 定稿
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': '#0f1115',
        'bg-panel': 'rgba(21,23,28,0.92)',
        'bg-nav': 'rgba(18,20,25,0.96)',
        'bg-card': 'rgba(255,255,255,0.05)',
        'bg-card-hover': 'rgba(255,255,255,0.09)',
        'bg-input': 'rgba(255,255,255,0.04)',
        'text-p': '#f9fafb',
        'text-s': '#a2a9b4',
        'text-t': '#6b7380',
        'text-inv': '#0b1420',
        'accent-cyan': '#99c8ff',
        'accent-violet': '#7ea2ff',
        'accent-warm': '#eab676',
        'accent-success': '#7dd3a8',
        'accent-danger': '#f28b82',
        'border-sub': 'rgba(255,255,255,0.08)',
        'border-glow': 'rgba(153,200,255,0.4)',
      },
      borderRadius: {
        panel: '18px',
        card: '14px',
        'card-sm': '10px',
        pill: '16px',
        btn: '10px',
        badge: '7px',
        'bubble-user': '12px',
        'bubble-ai': '12px',
      },
      boxShadow: {
        panel: '0 18px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)',
        card: '0 2px 12px rgba(0,0,0,0.25)',
        float: '0 8px 32px rgba(0,0,0,0.4)',
        'glow-accent': '0 0 0 2px rgba(153,200,255,0.18)',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        dotPulse: { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.3' } },
      },
      animation: {
        'fade-up': 'fadeUp 0.3s ease',
        pulse: 'dotPulse 1.5s infinite',
      },
    },
  },
  plugins: [],
}
