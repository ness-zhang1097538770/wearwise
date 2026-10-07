import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 允许通过 127.0.0.1 访问 dev 资源（避免 HMR/客户端 JS 被跨域拦截）
  allowedDevOrigins: ["127.0.0.1", "localhost"],
};

export default nextConfig;
