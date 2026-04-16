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
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
