/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
            colors: {
                brand: {
                    50: "#eff6ff",
                    100: "#dbeafe",
                    500: "#3b82f6",
                    600: "#2563eb",
                    700: "#1d4ed8",
                    900: "#1e3a8a",
                },
                surface: {
                    DEFAULT: "#0f172a",
                    card: "#1e293b",
                    border: "#334155",
                    muted: "#475569",
                },
            },
            animation: {
                shimmer: "shimmer 1.5s infinite linear",
                "fade-in": "fadeIn 0.3s ease-out",
                "slide-up": "slideUp 0.4s ease-out",
            },
            keyframes: {
                shimmer: {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" },
                },
                fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
                slideUp: { "0%": { transform: "translateY(16px)", opacity: "0" }, "100%": { transform: "translateY(0)", opacity: "1" } },
            },
        },
    },
    plugins: [],
};
