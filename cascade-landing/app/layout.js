import "./globals.css";
import { Suspense } from "react";
import PostHogProvider from "@/components/PostHogProvider";

export const viewport = {
  viewportFit: "cover",
};

export const metadata = {
  title: "Cascade | Your yearly goals die by March. Make them survive.",
  description:
    "Cascade is a goal execution system for builders. It turns yearly ambitions into daily actions that actually get done and adapts when they don't.",
  openGraph: {
    title: "Cascade | Your yearly goals die by March. Make them survive.",
    description:
      "Cascade is a goal execution system for builders. It turns yearly ambitions into daily actions that actually get done and adapts when they don't.",
    type: "website",
    url: "https://cascade-flame.vercel.app/",
    images: ["/cascade-og-image.png"],
  },
  twitter: {
    card: "summary_large_image",
    title: "Cascade | Your yearly goals die by March. Make them survive.",
    description:
      "Cascade is a goal execution system for builders. It turns yearly ambitions into daily actions that actually get done and adapts when they don't.",
    images: ["/cascade-twitter-card.png"],
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
      </head>
      <body>
        <Suspense fallback={null}>
          <PostHogProvider>{children}</PostHogProvider>
        </Suspense>
      </body>
    </html>
  );
}
