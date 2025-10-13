/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      typography: (theme) => ({
        DEFAULT: {
          css: {
            maxWidth: 'none',
            color: theme('colors.foreground'),
            '--tw-prose-body': theme('colors.foreground'),
            '--tw-prose-headings': theme('colors.foreground'),
            '--tw-prose-lead': theme('colors.muted.foreground'),
            '--tw-prose-links': theme('colors.primary.DEFAULT'),
            '--tw-prose-bold': theme('colors.foreground'),
            '--tw-prose-counters': theme('colors.muted.foreground'),
            '--tw-prose-bullets': theme('colors.muted.foreground'),
            '--tw-prose-hr': theme('colors.border'),
            '--tw-prose-quotes': theme('colors.foreground'),
            '--tw-prose-quote-borders': theme('colors.border'),
            '--tw-prose-captions': theme('colors.muted.foreground'),
            '--tw-prose-code': theme('colors.foreground'),
            '--tw-prose-pre-code': theme('colors.muted.foreground'),
            '--tw-prose-pre-bg': theme('colors.muted.DEFAULT'),
            '--tw-prose-th-borders': theme('colors.border'),
            '--tw-prose-td-borders': theme('colors.border'),
            'line-height': '1.6',
            'font-size': '0.95rem',
            p: {
              marginTop: '0.75em',
              marginBottom: '0.75em',
            },
            h1: {
              fontSize: '1.5rem',
              fontWeight: '700',
              marginTop: '0',
              marginBottom: '0.5em',
            },
            h2: {
              fontSize: '1.25rem',
              fontWeight: '600',
              marginTop: '1em',
              marginBottom: '0.5em',
            },
            h3: {
              fontSize: '1.1rem',
              fontWeight: '600',
              marginTop: '1em',
              marginBottom: '0.5em',
            },
            strong: {
              fontWeight: '600',
              color: theme('colors.foreground'),
            },
            em: {
              fontStyle: 'italic',
              color: theme('colors.foreground'),
            },
            blockquote: {
              fontStyle: 'italic',
              borderLeftWidth: '4px',
              borderLeftColor: theme('colors.primary.DEFAULT'),
              paddingLeft: '1rem',
              marginTop: '1em',
              marginBottom: '1em',
              color: theme('colors.muted.foreground'),
            },
            ul: {
              marginTop: '0.5em',
              marginBottom: '0.5em',
            },
            ol: {
              marginTop: '0.5em',
              marginBottom: '0.5em',
            },
            li: {
              marginTop: '0.25em',
              marginBottom: '0.25em',
            },
            // Custom dialogue formatting
            '.dialogue': {
              fontStyle: 'italic',
              paddingLeft: '1rem',
              borderLeft: `2px solid ${theme('colors.primary.DEFAULT')}`,
              marginTop: '0.5em',
              marginBottom: '0.5em',
            },
            '.character-name': {
              fontWeight: '600',
              color: theme('colors.primary.DEFAULT'),
            },
            '.narrative-action': {
              fontStyle: 'italic',
              color: theme('colors.muted.foreground'),
            }
          },
        },
        sm: {
          css: {
            fontSize: '0.875rem',
            lineHeight: '1.5',
          },
        },
        lg: {
          css: {
            fontSize: '1rem',
            lineHeight: '1.7',
          },
        },
      }),
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
