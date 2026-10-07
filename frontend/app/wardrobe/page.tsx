"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Upload, RefreshCw, Trash2, Pencil } from "lucide-react";
import { API_PREFIX, assetUrl } from "../lib/api";

type Garment = {
  id: number;
  name: string;
  category: string;
  color: string;
  pattern: string;
  material: string;
  fit: string;
  season: string;
  cutout_url?: string | null;
  image_url?: string | null;
  status: string;
};

const CATEGORIES = ["全部", "上装", "下装", "外套", "连衣裙", "鞋", "包", "配饰"];

export default function Wardrobe() {
  const [garments, setGarments] = useState<Garment[]>([]);
  const [filter, setFilter] = useState("全部");
  const [uploading, setUploading] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() => {
    fetch(`${API_PREFIX}/garments`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setGarments)
      .catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = filter === "全部" ? garments : garments.filter((g) => g.category === filter);

  async function onUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    const fd = new FormData();
    for (const f of Array.from(files)) fd.append("files", f);
    await fetch(`${API_PREFIX}/garments`, { method: "POST", body: fd });
    setUploading(false);
    load();
  }

  async function reRecognize(id: number) {
    await fetch(`${API_PREFIX}/garments/${id}/recognize`, { method: "POST" });
    load();
  }

  async function remove(id: number) {
    if (!confirm("确认删除这件衣物？")) return;
    await fetch(`${API_PREFIX}/garments/${id}`, { method: "DELETE" });
    load();
  }

  async function saveName(id: number) {
    if (!editName.trim()) return;
    await fetch(`${API_PREFIX}/garments/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: editName.trim() }),
    });
    setEditingId(null);
    load();
  }

  return (
    <div className="mx-auto max-w-6xl">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="font-serif text-3xl text-ink-1">我的衣橱</h1>
          <p className="mt-1 text-sm text-ink-2">共 {garments.length} 件 · 上传照片自动去背景识别</p>
        </div>
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="grad-violet flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium text-white shadow-sm disabled:opacity-50"
        >
          <Upload size={16} />
          {uploading ? "上传中…" : "添加衣物"}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={(e) => onUpload(e.target.files)}
        />
      </header>

      {/* 分类筛选 */}
      <div className="mt-5 flex flex-wrap gap-2">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            className={`rounded-full px-4 py-1.5 text-sm transition-colors ${
              filter === c ? "grad-violet text-white" : "bg-white text-ink-2 ring-1 ring-bone-2"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {/* 衣物网格 */}
      {filtered.length === 0 ? (
        <div className="grad-aurora mt-6 rounded-lg p-16 text-center">
          <p className="text-sm text-ink-1">衣橱还是空的</p>
          <p className="mt-1 text-[13px] text-ink-2">拍一张衣服照片，AI 会自动去背景建档</p>
          <button
            onClick={() => fileRef.current?.click()}
            className="grad-terra mt-5 rounded-full px-6 py-2.5 text-sm text-white"
          >
            添加第一件
          </button>
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {filtered.map((g) => (
            <div key={g.id} className="card-soft hover-lift rounded-lg bg-white p-3 ring-1 ring-bone-2">
              <div className="flex h-44 items-center justify-center rounded-sm bg-bone-1">
                {g.cutout_url || g.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={assetUrl(g.cutout_url || g.image_url!)}
                    alt={g.name}
                    className="h-full w-full rounded-sm object-contain"
                  />
                ) : (
                  <span className="font-serif text-sm text-bone-3">无图</span>
                )}
              </div>

              <div className="mt-2">
                {editingId === g.id ? (
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onBlur={() => saveName(g.id)}
                    onKeyDown={(e) => e.key === "Enter" && saveName(g.id)}
                    autoFocus
                    className="w-full rounded-sm border border-bone-2 px-2 py-1 text-sm outline-none focus:border-violet-400"
                  />
                ) : (
                  <p className="truncate text-sm font-medium text-ink-1">{g.name || "未命名"}</p>
                )}
                <p className="mt-0.5 text-xs text-ink-2">
                  {g.category} · {g.color} · {g.material}
                </p>
              </div>

              <div className="mt-2 flex items-center justify-between text-ink-2">
                <span className="text-xs">{g.status === "confirmed" ? "已确认" : "待确认"}</span>
                <div className="flex gap-1">
                  <button
                    title="重命名"
                    onClick={() => {
                      setEditingId(g.id);
                      setEditName(g.name);
                    }}
                    className="rounded-full p-1.5 hover:bg-bone-1"
                  >
                    <Pencil size={14} />
                  </button>
                  <button title="重新识别" onClick={() => reRecognize(g.id)} className="rounded-full p-1.5 hover:bg-bone-1">
                    <RefreshCw size={14} />
                  </button>
                  <button title="删除" onClick={() => remove(g.id)} className="rounded-full p-1.5 hover:bg-terra-50">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
