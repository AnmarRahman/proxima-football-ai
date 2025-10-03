import { AIChatWidget } from "@/components/ai-chat-widget"
import { Analytics } from "@vercel/analytics/next"
import type { Metadata } from "next"
import { Montserrat } from "next/font/google"
import { Suspense } from "react"
import "./globals.css"

const montserrat = Montserrat({
  subsets: ["latin"],
  weight: ["700"], // Bold only
  variable: "--font-montserrat",
})

export const metadata: Metadata = {
  title: "Proxima Football AI - Predicting the Beautiful Game",
  description:
    "Advanced AI-powered football analytics, player predictions, and career insights. Discover the future of football with cutting-edge artificial intelligence.",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${montserrat.variable} font-sans antialiased uppercase`}>
        <Suspense fallback={null}>{children}</Suspense>
        <AIChatWidget />
        <Analytics />
      </body>
    </html>
  )
}
