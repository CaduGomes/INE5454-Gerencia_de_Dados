import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Busca de Video Games',
  description: 'Busque e filtre video games de diferentes lojas',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-50 min-h-screen" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}

