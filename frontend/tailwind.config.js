/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Google Material palette
        gm: {
          blue: '#1a73e8',
          'blue-hover': '#1765cc',
          'blue-light': '#e8f0fe',
          'blue-surface': '#d2e3fc',
          red: '#d93025',
          'red-light': '#fce8e6',
          green: '#1e8e3e',
          'green-light': '#e6f4ea',
          yellow: '#f9ab00',
          'yellow-light': '#fef7e0',
          orange: '#e8710a',
        },
        surface: {
          DEFAULT: '#ffffff',
          dim: '#f8f9fa',
          container: '#f1f3f4',
          'container-high': '#e8eaed',
          'container-highest': '#dadce0',
        },
        on: {
          surface: '#202124',
          'surface-variant': '#5f6368',
          primary: '#1a73e8',
          error: '#d93025',
        },
        outline: {
          DEFAULT: '#dadce0',
          variant: '#e8eaed',
        },
        // NHS accent retained for branding
        nhs: {
          blue: '#005eb8',
          'dark-blue': '#003087',
        },
      },
      fontFamily: {
        sans: ['"Google Sans"', '"Roboto"', 'Arial', 'sans-serif'],
      },
      fontSize: {
        'display-lg': ['3rem', { lineHeight: '3.5rem', fontWeight: '400' }],
        'display-md': ['2.25rem', { lineHeight: '2.75rem', fontWeight: '400' }],
        'display-sm': ['1.75rem', { lineHeight: '2.25rem', fontWeight: '400' }],
        'headline-lg': ['1.5rem', { lineHeight: '2rem', fontWeight: '400' }],
        'headline-md': ['1.25rem', { lineHeight: '1.75rem', fontWeight: '500' }],
        'title-lg': ['1.125rem', { lineHeight: '1.5rem', fontWeight: '500' }],
        'title-md': ['1rem', { lineHeight: '1.5rem', fontWeight: '500' }],
        'title-sm': ['0.875rem', { lineHeight: '1.25rem', fontWeight: '500' }],
        'body-lg': ['1rem', { lineHeight: '1.5rem', fontWeight: '400' }],
        'body-md': ['0.875rem', { lineHeight: '1.25rem', fontWeight: '400' }],
        'label-lg': ['0.875rem', { lineHeight: '1.25rem', fontWeight: '500' }],
        'label-md': ['0.75rem', { lineHeight: '1rem', fontWeight: '500' }],
      },
      borderRadius: {
        'gm-sm': '8px',
        'gm-md': '12px',
        'gm-lg': '16px',
        'gm-xl': '28px',
      },
      boxShadow: {
        'gm-1': '0 1px 2px 0 rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15)',
        'gm-2': '0 1px 2px 0 rgba(60,64,67,.3), 0 2px 6px 2px rgba(60,64,67,.15)',
        'gm-3': '0 1px 3px 0 rgba(60,64,67,.3), 0 4px 8px 3px rgba(60,64,67,.15)',
        'gm-4': '0 2px 3px 0 rgba(60,64,67,.3), 0 6px 10px 4px rgba(60,64,67,.15)',
      },
    },
  },
  plugins: [],
};
