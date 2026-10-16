/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  env: {
    NEXT_PUBLIC_DEPLOYMENT_VARIANT: 'vps',
  },
};

module.exports = nextConfig;
