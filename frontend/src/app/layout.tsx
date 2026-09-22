import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Athena",
  description: "Track your job search and build your territory as you go.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-stone-50 font-sans text-stone-900">
        {children}
      </body>
    </html>
  );
}
