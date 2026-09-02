/** @type {import('tailwindcss').Config} */

/*
 * Design tokens for a clinical data tool.
 *
 * The brief is a working instrument, not a consumer app: information density
 * over generous whitespace, hairline borders instead of drop shadows to
 * separate regions, tight corner radii, and a restrained palette where colour
 * carries meaning rather than decoration. Shadows are reserved for things that
 * genuinely float above the page — menus, dialogs.
 *
 * The token *names* are inherited from the previous Material-flavoured system.
 * Renaming them across every component would have been churn for no benefit,
 * so the names stayed and the values changed.
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        gm: {
          // A deep, low-chroma blue. Bright enough to read as interactive,
          // restrained enough not to compete with clinical status colours.
          blue: '#1d4ed8',
          'blue-hover': '#1a43b8',
          'blue-light': '#eef2ff',
          'blue-surface': '#dbe4fe',
          red: '#b42318',
          'red-light': '#fef3f2',
          green: '#067647',
          'green-light': '#ecfdf3',
          yellow: '#b54708',
          'yellow-light': '#fffaeb',
          orange: '#c4320a',
        },
        surface: {
          DEFAULT: '#ffffff',
          dim: '#f7f8fa',
          container: '#f1f3f6',
          'container-high': '#e7eaef',
          'container-highest': '#dbdfe6',
        },
        on: {
          surface: '#12161f',
          'surface-variant': '#5b6472',
          primary: '#1d4ed8',
          error: '#b42318',
        },
        outline: {
          DEFAULT: '#dfe3e9',
          variant: '#edf0f4',
        },
        nhs: {
          blue: '#005eb8',
          'dark-blue': '#003087',
        },
      },
      fontFamily: {
        // System stack: no webfont request, no CSP exception, and it renders
        // as SF Pro / Segoe UI natively — which is what a desktop tool should
        // look like. The previous Google Fonts @import was blocked by this
        // app's own Content-Security-Policy and never actually loaded.
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Inter',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ],
        mono: [
          'ui-monospace',
          'SFMono-Regular',
          '"SF Mono"',
          'Menlo',
          'Consolas',
          '"Liberation Mono"',
          'monospace',
        ],
      },
      fontSize: {
        // Denser than the Material scale it replaces. 13px body is the working
        // size for tables and forms; anything larger wastes rows.
        'display-lg': ['1.75rem', { lineHeight: '2.25rem', fontWeight: '650', letterSpacing: '-0.02em' }],
        'display-md': ['1.5rem', { lineHeight: '2rem', fontWeight: '650', letterSpacing: '-0.02em' }],
        'display-sm': ['1.3125rem', { lineHeight: '1.75rem', fontWeight: '650', letterSpacing: '-0.015em' }],
        'headline-lg': ['1.125rem', { lineHeight: '1.625rem', fontWeight: '600', letterSpacing: '-0.01em' }],
        'headline-md': ['1rem', { lineHeight: '1.5rem', fontWeight: '600' }],
        'title-lg': ['0.9375rem', { lineHeight: '1.375rem', fontWeight: '600' }],
        'title-md': ['0.875rem', { lineHeight: '1.25rem', fontWeight: '600' }],
        'title-sm': ['0.8125rem', { lineHeight: '1.125rem', fontWeight: '600' }],
        'body-lg': ['0.875rem', { lineHeight: '1.375rem', fontWeight: '400' }],
        'body-md': ['0.8125rem', { lineHeight: '1.25rem', fontWeight: '400' }],
        'label-lg': ['0.8125rem', { lineHeight: '1.125rem', fontWeight: '500' }],
        'label-md': ['0.75rem', { lineHeight: '1rem', fontWeight: '500' }],
        'label-sm': ['0.6875rem', { lineHeight: '0.875rem', fontWeight: '600', letterSpacing: '0.04em' }],
      },
      borderRadius: {
        'gm-sm': '4px',
        'gm-md': '6px',
        'gm-lg': '8px',
        // Was a 28px pill. Rounded rectangles read as tools; pills read as
        // consumer apps.
        'gm-xl': '6px',
      },
      boxShadow: {
        // Barely-there. Structure comes from borders; these are for the few
        // things that really do float.
        'gm-1': '0 1px 2px 0 rgba(16,24,40,0.04)',
        'gm-2': '0 1px 3px 0 rgba(16,24,40,0.08), 0 1px 2px -1px rgba(16,24,40,0.04)',
        'gm-3': '0 4px 8px -2px rgba(16,24,40,0.10), 0 2px 4px -2px rgba(16,24,40,0.05)',
        'gm-4': '0 12px 20px -6px rgba(16,24,40,0.12), 0 4px 8px -4px rgba(16,24,40,0.06)',
      },
      spacing: {
        18: '4.5rem',
      },
    },
  },
  plugins: [],
};
