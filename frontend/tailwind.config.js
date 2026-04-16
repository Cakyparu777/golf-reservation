/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        green: {
          950: '#0d2318',
          900: '#1a3d2b',
          800: '#1e4d33',
          700: '#2d6a4f',
          600: '#3a8a66',
        },
        gold: {
          500: '#c8922a',
          400: '#d4a645',
          300: '#e8c572',
        },
        surface: {
          DEFAULT: '#f4f6f0',
          card: '#ffffff',
          muted: '#fafbf7',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        '4xl': '2rem',
      },
      boxShadow: {
        soft: '0 1px 3px rgba(0,0,0,.04), 0 1px 2px rgba(0,0,0,.03)',
        card: '0 4px 12px rgba(0,0,0,.06), 0 2px 4px rgba(0,0,0,.03)',
        elevated: '0 12px 40px rgba(0,0,0,.08), 0 4px 12px rgba(0,0,0,.04)',
        glow: '0 0 20px rgba(26,61,43,.12)',
      },
      animation: {
        fadeIn: 'fadeIn .4s ease-out both',
        slideUp: 'slideUp .45s cubic-bezier(.22,1,.36,1) both',
        slideDown: 'slideDown .35s ease-out both',
        scaleIn: 'scaleIn .3s cubic-bezier(.22,1,.36,1) both',
        pulseSoft: 'pulseSoft 2s ease-in-out infinite',
        float: 'float 3s ease-in-out infinite',
        shimmer: 'shimmer 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(12px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          from: { opacity: '0', transform: 'scale(.92)' },
          to: { opacity: '1', transform: 'scale(1)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '.7' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-6px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      transitionTimingFunction: {
        spring: 'cubic-bezier(.22,1,.36,1)',
      },
    },
  },
  plugins: [],
}
