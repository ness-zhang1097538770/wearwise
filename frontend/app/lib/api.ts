// API 客户端：直连后端
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8002";
export const API_PREFIX = `${API_BASE}/api/v1`;

export async function apiGet<T = unknown>(path: string): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`);
  if (!res.ok) throw new Error(`请求失败 ${res.status}`);
  return res.json();
}

export async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_PREFIX}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`请求失败 ${res.status}`);
  return res.json();
}

// 后端返回的相对图片地址（如 /static/uploads/xxx.jpg）补全为完整地址
export function assetUrl(path: string | null | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_BASE}${path}`;
}
