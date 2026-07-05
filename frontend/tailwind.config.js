/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./landingpage.html",
    "./login.html",
    "./chat.html",
    "./onboarding.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "sage-muted": "#5E827D",
        "tertiary": "#3c3b39",
        "surface-bright": "#f9f9ff",
        "on-primary": "#ffffff",
        "surface-dim": "#d3daea",
        "on-secondary-fixed-variant": "#474554",
        "on-tertiary": "#ffffff",
        "error-container": "#ffdad6",
        "on-secondary-fixed": "#1b1a27",
        "surface-container-lowest": "#ffffff",
        "inverse-primary": "#a1d0c8",
        "secondary-fixed-dim": "#c8c4d7",
        "on-secondary-container": "#636171",
        "outline": "#707977",
        "surface-container": "#e7eefe",
        "lavender-soft": "#E3DFF2",
        "background": "#f9f9ff",
        "mood-advice": "#D7F2E2",
        "mood-venting": "#F2D7D7",
        "on-tertiary-fixed": "#1c1c19",
        "on-surface-variant": "#404847",
        "tertiary-fixed-dim": "#c9c6c2",
        "surface-container-high": "#e2e8f8",
        "inverse-on-surface": "#ebf1ff",
        "error": "#ba1a1a",
        "on-primary-fixed": "#00201d",
        "tertiary-container": "#54524f",
        "lavender-dark": "#7C73A7",
        "secondary": "#5e5d6c",
        "secondary-container": "#e1ddf0",
        "surface-container-low": "#f0f3ff",
        "on-tertiary-fixed-variant": "#484744",
        "on-background": "#151c27",
        "inverse-surface": "#2a313d",
        "on-surface": "#151c27",
        "tertiary-fixed": "#e6e2de",
        "on-primary-fixed-variant": "#204e48",
        "sage-deep": "#2D5A54",
        "primary-container": "#2d5a54",
        "primary-fixed-dim": "#a1d0c8",
        "mood-exploring": "#D7EAF2",
        "surface": "#f9f9ff",
        "on-tertiary-container": "#c9c5c2",
        "on-primary-container": "#a1cfc8",
        "primary-fixed": "#bcece4",
        "on-error-container": "#93000a",
        "linen-bg": "#FAF9F6",
        "on-secondary": "#ffffff",
        "secondary-fixed": "#e4e0f3",
        "primary": "#13423d",
        "outline-variant": "#c0c8c6",
        "on-error": "#ffffff",
        "surface-variant": "#dce2f3",
        "surface-tint": "#396660",
        "surface-container-highest": "#dce2f3"
      },
      borderRadius: {
        "DEFAULT": "0.25rem",
        "lg": "0.5rem",
        "xl": "0.75rem",
        "full": "9999px"
      },
      spacing: {
        "container-max": "1200px",
        "stack-sm": "8px",
        "margin-mobile": "20px",
        "margin-desktop": "40px",
        "stack-md": "16px",
        "stack-lg": "32px",
        "gutter": "24px",
        "section-gap": "64px"
      },
      fontFamily: {
        "display-lg": ["Literata", "serif"],
        "label-sm": ["Inter", "sans-serif"],
        "body-md": ["Inter", "sans-serif"],
        "headline-md": ["Literata", "serif"],
        "body-lg": ["Inter", "sans-serif"],
        "headline-lg-mobile": ["Literata", "serif"],
        "headline-lg": ["Literata", "serif"],
        "label-md": ["Inter", "sans-serif"]
      },
      fontSize: {
        "display-lg": [
          "48px",
          {
            "lineHeight": "56px",
            "letterSpacing": "-0.02em",
            "fontWeight": "700"
          }
        ],
        "label-sm": [
          "12px",
          {
            "lineHeight": "16px",
            "letterSpacing": "0.05em",
            "fontWeight": "600"
          }
        ],
        "body-md": [
          "16px",
          {
            "lineHeight": "24px",
            "fontWeight": "400"
          }
        ],
        "headline-md": [
          "24px",
          {
            "lineHeight": "32px",
            "fontWeight": "600"
          }
        ],
        "body-lg": [
          "18px",
          {
            "lineHeight": "28px",
            "fontWeight": "400"
          }
        ],
        "headline-lg-mobile": [
          "32px",
          {
            "lineHeight": "40px",
            "fontWeight": "700"
          }
        ],
        "headline-lg": [
          "40px",
          {
            "lineHeight": "48px",
            "fontWeight": "700"
          }
        ],
        "label-md": [
          "14px",
          {
            "lineHeight": "20px",
            "fontWeight": "600"
          }
        ]
      }
    }
  },
  plugins: [],
}
