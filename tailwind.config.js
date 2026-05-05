/**
 * Tailwind config — design tokens ported from the new CourtListener
 * front-end design (`courtlistener/cl/assets/tailwind/tailwind.config.js`)
 * so the demo site renders visually identical to production CL.
 *
 * If CL updates its tokens, sync them here.
 */
module.exports = {
  content: [
    "./src/**/*.{njk,md,html}",
    "./_includes/**/*.{njk,md,html}",
  ],
  theme: {
    extend: {
      screens: {
        xs: "392px",
      },
      spacing: {
        4.5: "1.125rem",
        7.5: "1.875rem",
        13: "3.25rem",
        15: "3.75rem",
        18: "4.5rem",
        21: "5.25rem",
        26: "6.5rem",
        35: "8.75rem",
        41: "10.25rem",
        42: "10.5rem",
        45: "11.25rem",
        53: "13.25rem",
        55: "13.75rem",
        70: "17.5rem",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        cooper: ["Cooper Hewitt", "sans-serif"],
        mono: ["DM Mono", "mono"],
      },
      colors: {
        greyscale: {
          25: "#FDFCFB",
          50: "#FBFAF8",
          100: "#F5F3EF",
          200: "#E8E4DE",
          300: "#D6D0C6",
          400: "#A8A091",
          500: "#776F61",
          600: "#574F40",
          700: "#453F35",
          800: "#29261F",
          900: "#1C1814",
          950: "#171411",
        },
        primary: {
          25: "#FDF9F7",
          50: "#FBF4EF",
          100: "#F7E6DE",
          200: "#EFCBBD",
          300: "#E19684",
          400: "#D56958",
          500: "#CD4137",
          600: "#B5362D",
          700: "#9B2E27",
          800: "#832720",
          900: "#6A201A",
          950: "#4E1713",
        },
        brand: {
          100: "#F4EBFF",
          300: "#D6BBFB",
          600: "#7F56D9",
          700: "#6941C6",
        },
        yellow: {
          50: "#FFFAEB",
          400: "#FDB022",
        },
        amber: {
          450: "#FDB022",
        },
        blue: {
          700: "#004EEB",
        },
        red: {
          400: "#FF692E",
          500: "#E62E05",
        },
      },
      fontSize: {
        xs: ["12px", "18px"],
        "xs-cooper": ["12px", "18px"],
        sm: ["14px", "20px"],
        md: ["16px", "24px"],
        lg: ["18px", "28px"],
        "lg-cooper": ["18px", "26px"],
        xl: ["20px", "28px"],
        "display-xxs": ["18px", "28px"],
        "display-xs": ["24px", "32px"],
        "display-sm": ["30px", "38px"],
        "display-sm-cooper": ["28px", "44px"],
        "display-md": ["32px", "40px"],
        "display-lg": ["40px", "48px"],
        "display-xl": ["44px", "52px"],
      },
      maxWidth: {
        content: "948px",
      },
    },
  },
  plugins: [],
};
