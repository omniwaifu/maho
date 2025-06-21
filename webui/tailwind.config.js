/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./js/**/*.{js,ts}",
    "./components/**/*.{html,js}",
    // Add paths to any files that contain Tailwind class names
  ],
  darkMode: 'class', // matches your existing dark-mode class
  theme: {
    extend: {
      colors: {
        // Map your existing CSS variables to Tailwind
        'maho': {
          'bg': 'var(--color-background)',
          'text': 'var(--color-text)',
          'primary': 'var(--color-primary)',
          'secondary': 'var(--color-secondary)',
          'accent': 'var(--color-accent)',
          'panel': 'var(--color-panel)',
          'border': 'var(--color-border)',
          'input': 'var(--color-input)',
          'input-focus': 'var(--color-input-focus)',
          'message-bg': 'var(--color-message-bg)',
          'message-text': 'var(--color-message-text)',
        }
      },
      fontFamily: {
        'sans': ['Geist', 'system-ui', 'sans-serif'],
        'mono': ['Geist Mono', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'maho-sm': 'var(--font-size-small)',
        'maho-base': 'var(--font-size-normal)',
        'maho-lg': 'var(--font-size-large)',
        'maho-msg': 'var(--font-size-message)',
      },
      spacing: {
        'maho-xs': 'var(--spacing-xs)',
        'maho-sm': 'var(--spacing-sm)',
        'maho-md': 'var(--spacing-md)',
        'maho-lg': 'var(--spacing-lg)',
      },
      borderRadius: {
        'maho': 'var(--border-radius)',
      },
      transitionDuration: {
        'maho': 'var(--transition-speed)',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
} 