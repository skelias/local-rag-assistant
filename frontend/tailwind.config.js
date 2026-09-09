/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': '#0f0f12',
        'bg-panel': 'rgba(28,28,32,0.72)',
        'bg-nav': 'rgba(22,22,26,0.88)',
        'bg-card': 'rgba(255,255,255,0.055)',
        'bg-card-hover': 'rgba(255,255,255,0.095)',
        'bg-input': 'rgba(255,255,255,0.04)',
        'text-p': '#f0f0f5',
        'text-s': '#a0a0b0',
        'text-t': '#6e6e7a',
        'text-inv': '#121216',
        'accent-cyan': '#4ecdc4',
        'accent-violet': '#a78bfa',
        'accent-warm': '#f4a261',
        'accent-success': '#2ecc71',
        'accent-danger': '#e74c3c',
        'border-sub': 'rgba(255,255,255,0.07)',
        'border-glow': 'rgba(78,205,196,0.35)',
      },
      borderRadius: {
        panel: '28px',
        card: '20px',
        'card-sm': '14px',
        pill: '24px',
        btn: '12px',
        badge: '8px',
        'bubble-user': '20px 20px 4px 20px',
        'bubble-ai': '4px 20px 20px 20px',
      },
      boxShadow: {
        panel: '0 24px 70px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.04)',
        card: '0 4px 20px rgba(0,0,0,0.25)',
        float: '0 8px 32px rgba(0,0,0,0.35)',
        'glow-cyan': '0 0 0 1px rgba(78,205,196,0.35)',
      },
      backdropBlur: {
        panel: '22px',
        nav: '24px',
        drawer: '28px',
      },
      animation: {
        'fade-up': 'fadeUp 0.35s ease',
        pulse: 'dotPulse 1.5s infinite',
        'slide-right': 'slideRight 0.35s cubic-bezier(0.16,1,0.3,1)',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        dotPulse: {
          '0%,100%': { opacity: '1' },
          '50%': { opacity: '0.3' },
        },
        slideRight: {
          from: { transform: 'translateX(100%)' },
          to: { transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
