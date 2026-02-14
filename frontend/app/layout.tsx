import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Manrope, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/shared/theme-provider";
import { ReactQueryProvider } from "@/components/shared/react-query-provider";
import { fallbackLng } from "@/lib/i18n/settings";
import { Toaster } from "@/components/ui/sonner";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const manrope = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export const metadata: Metadata = {
  title: "Poco",
  description: "A multi-service AI agent execution platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang={fallbackLng} suppressHydrationWarning className="h-full">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${manrope.variable} ${spaceGrotesk.variable} antialiased h-full`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <ReactQueryProvider>
            {children}
            <Toaster position="top-right" />
          </ReactQueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
