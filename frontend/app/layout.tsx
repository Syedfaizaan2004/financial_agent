import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
    title: "Financial Research Agent",
    description: "AI-powered stock research, risk analysis, and investment insights",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <body className="min-h-screen bg-surface text-slate-100 antialiased">
                {children}
            </body>
        </html>
    );
}
