import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme/ThemeProvider";
import { Sidebar } from "@/components/layout/Sidebar";
import { BottomNav } from "@/components/layout/BottomNav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Univora Button Bot",
  description: "Create stunning Telegram posts with interactive buttons.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        suppressHydrationWarning
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <div className="flex min-h-screen bg-background">
            <Sidebar />
            <main className="flex-1 md:ml-72 pb-24 md:pb-0 overflow-y-auto min-h-screen">
              <div className="max-w-5xl mx-auto p-4 md:p-10 lg:p-12 mt-4 md:mt-0">
                {children}
              </div>
            </main>
            <BottomNav />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
