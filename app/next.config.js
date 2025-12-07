/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.mlstatic.com',
      },
      {
        protocol: 'https',
        hostname: '**.mlcdn.com.br',
      },
    ],
  },
}

module.exports = nextConfig

