/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone', // Enable standalone output for Docker
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
  // Add timeout configuration for API routes
  experimental: {
    // Increase timeout for long-running requests
    serverComponentsExternalPackages: [],
  },
  // Increase timeout for long-running API requests
  serverRuntimeConfig: {
    // Timeout for API proxy requests (in milliseconds)
    apiTimeout: 30000, // 30 seconds
  },
}

module.exports = nextConfig

