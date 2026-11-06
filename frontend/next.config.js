/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  env: { NEXT_PUBLIC_DEPLOYMENT_VARIANT: 'vps-c' },
};

module.exports = nextConfig;
