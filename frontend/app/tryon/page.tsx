"use client";

import { useCallback, useEffect, useState } from "react";
import { Sparkles, Video, Wand2 } from "lucide-react";
import { API_PREFIX, assetUrl } from "../lib/api";

type Avatar = {
  id: number;
  candidates: { index: number; image_url: string }[];
  selected: number | null;
  is_primary: boolean;
  status: string;
};
type Outfit = { id: number; result: { outfits: { name: string }[] } };

async function pollTask(taskId: number): Promise<{ status: string; result: Record<string, unknown>; error: string }> {
  for (let i = 0; i < 120; i++) {
    const res = await fetch(`${API_PREFIX}/tasks/${taskId}`);
    const t = await res.json();
    if (t.status === "done" || t.status === "failed") return t;
    await new Promise((r) => setTimeout(r, 1500));
  }
  return { status: "failed", result: {}, error: "超时" };
}

export default function TryOn() {
  const [avatars, setAvatars] = useState<Avatar[]>([]);
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [params, setParams] = useState({ height: "", build: "", skin: "", hair: "" });
  const [generating, setGenerating] = useState(false);
  const [resultImg, setResultImg] = useState<string | null>(null);
  const [resultVideo, setResultVideo] = useState<string | null>(null);
  const [busy, setBusy] = useState("");
  const [outfitId, setOutfitId] = useState<number | null>(null);
  const [itemIdx, setItemIdx] = useState(0);

  const load = useCallback(() => {
    fetch(`${API_PREFIX}/avatars`).then((r) => r.ok && r.json()).then(setAvatars).catch(() => {});
    fetch(`${API_PREFIX}/outfits`).then((r) => r.ok && r.json()).then(setOutfits).catch(() => {});
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => {
      // 后台生成候选时轮询
      fetch(`${API_PREFIX}/avatars`).then((r) => r.ok && r.json()).then((list: Avatar[]) => {
        if (list.some((a) => a.status === "running" || a.status === "pending")) load();
      }).catch(() => {});
    }, 5000);
    return () => clearInterval(t);
  }, [load]);

  const primary = avatars.find((a) => a.is_primary);

  async function generateAvatar() {
    setGenerating(true);
    await fetch(`${API_PREFIX}/avatars`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(params),
    });
    // 轮询直到候选生成完
    for (let i = 0; i < 60; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const list = (await (await fetch(`${API_PREFIX}/avatars`)).json()) as Avatar[];
      const latest = list[0];
      if (latest && latest.status === "done") break;
    }
    setGenerating(false);
    load();
  }

  async function selectAvatar(id: number, index: number) {
    await fetch(`${API_PREFIX}/avatars/${id}/select`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index }),
    });
    load();
  }

  async function genImage() {
    if (outfitId == null) return;
    setBusy("生成上身图中…");
    setResultImg(null);
    setResultVideo(null);
    const res = await fetch(`${API_PREFIX}/outfits/${outfitId}/items/${itemIdx}/avatar-image`, { method: "POST" });
    const { task_id } = await res.json();
    const t = await pollTask(task_id);
    if (t.status === "done") setResultImg(assetUrl(t.result.image_url as string));
    setBusy("");
  }

  async function genVideo() {
    if (outfitId == null) return;
    setBusy("生成试穿视频中（约 1-3 分钟）…");
    setResultVideo(null);
    const res = await fetch(`${API_PREFIX}/outfits/${outfitId}/items/${itemIdx}/video`, { method: "POST" });
    const { task_id } = await res.json();
    const t = await pollTask(task_id);
    if (t.status === "done" && t.result.video_url) setResultVideo(assetUrl(t.result.video_url as string));
    setBusy("");
  }

  const latestAvatar = avatars[0];

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="font-serif text-3xl text-ink-1">AI 试穿</h1>
      <p className="mt-1 text-sm text-ink-2">不传真人照片，用体型参数生成专属数字形象</p>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 左：数字形象 */}
        <section className="card-soft rounded-lg bg-white p-5 ring-1 ring-bone-2">
          <h2 className="flex items-center gap-2 text-base font-medium text-ink-1">
            <Wand2 size={18} className="text-violet-600" /> 数字形象（Avatar）
          </h2>

          {/* 参数表单 */}
          <div className="mt-4 grid grid-cols-2 gap-3">
            {[
              { key: "height", label: "身高", ph: "如 165cm" },
              { key: "build", label: "体型", ph: "如 中等偏瘦" },
              { key: "skin", label: "肤色", ph: "如 自然肤色" },
              { key: "hair", label: "发色发型", ph: "如 黑色长发" },
            ].map((f) => (
              <div key={f.key}>
                <label className="text-xs text-ink-2">{f.label}</label>
                <input
                  value={params[f.key as keyof typeof params]}
                  onChange={(e) => setParams({ ...params, [f.key]: e.target.value })}
                  placeholder={f.ph}
                  className="mt-1 w-full rounded-sm border border-bone-2 px-3 py-2 text-sm outline-none focus:border-violet-400"
                />
              </div>
            ))}
          </div>
          <button
            onClick={generateAvatar}
            disabled={generating}
            className="grad-violet mt-4 flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
          >
            <Sparkles size={16} />
            {generating ? "生成中（约 1 分钟）…" : "生成 4 个候选"}
          </button>

          {/* 候选 */}
          {latestAvatar && latestAvatar.status === "done" && (
            <div className="mt-5">
              <p className="text-xs text-ink-2">点一个设为主形象：</p>
              <div className="mt-2 grid grid-cols-4 gap-2">
                {latestAvatar.candidates.map((c) => (
                  <button
                    key={c.index}
                    onClick={() => selectAvatar(latestAvatar.id, c.index)}
                    className={`overflow-hidden rounded-sm ${
                      latestAvatar.selected === c.index ? "ring-2 ring-terra-600" : "ring-1 ring-bone-2"
                    }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={assetUrl(c.image_url)} alt={`候选 ${c.index + 1}`} className="h-24 w-full object-cover" />
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 当前主形象 */}
          {primary && primary.selected != null && (
            <div className="mt-5 rounded-md grad-card p-3 text-sm text-ink-2">
              ✅ 当前主形象：
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={assetUrl(primary.candidates[primary.selected]?.image_url)}
                alt="主形象"
                className="mt-2 h-32 rounded-sm object-contain"
              />
            </div>
          )}
        </section>

        {/* 右：上身图 / 视频 */}
        <section className="card-soft rounded-lg bg-white p-5 ring-1 ring-bone-2">
          <h2 className="flex items-center gap-2 text-base font-medium text-ink-1">
            <Sparkles size={18} className="text-violet-600" /> 上身图 · 试穿视频
          </h2>

          {/* 选穿搭 */}
          <div className="mt-4">
            <label className="text-xs text-ink-2">选一套穿搭方案</label>
            <select
              value={outfitId ?? ""}
              onChange={(e) => setOutfitId(Number(e.target.value))}
              className="mt-1 w-full rounded-sm border border-bone-2 px-3 py-2 text-sm outline-none focus:border-violet-400"
            >
              <option value="" disabled>
                请选择
              </option>
              {outfits.map((o) => (
                <option key={o.id} value={o.id}>
                  方案 #{o.id}
                </option>
              ))}
            </select>
            <label className="mt-3 block text-xs text-ink-2">第几套（0 开始）</label>
            <input
              type="number"
              min={0}
              max={2}
              value={itemIdx}
              onChange={(e) => setItemIdx(Number(e.target.value))}
              className="mt-1 w-24 rounded-sm border border-bone-2 px-3 py-2 text-sm outline-none focus:border-violet-400"
            />
          </div>

          <div className="mt-4 flex gap-2">
            <button
              onClick={genImage}
              disabled={outfitId == null || !!busy}
              className="grad-violet flex-1 rounded-full py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              生成上身图
            </button>
            <button
              onClick={genVideo}
              disabled={outfitId == null || !!busy}
              className="grad-terra flex flex-1 items-center justify-center gap-1.5 rounded-full py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              <Video size={16} /> 生成视频
            </button>
          </div>

          {busy && <p className="mt-3 text-sm text-violet-800">{busy}</p>}

          {resultImg && (
            <div className="mt-4">
              <p className="text-xs text-ink-2">上身图（AI 生成参考）：</p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={resultImg} alt="上身图" className="mt-2 max-h-80 rounded-sm object-contain" />
            </div>
          )}
          {resultVideo && (
            <div className="mt-4">
              <p className="text-xs text-ink-2">试穿视频：</p>
              <video src={resultVideo} controls className="mt-2 w-full rounded-sm" />
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
