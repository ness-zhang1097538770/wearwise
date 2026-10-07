"use client";

import { useEffect, useState } from "react";
import { API_PREFIX, assetUrl } from "./lib/api";

type Garment = {
  id: number;
  name: string;
  category: string;
  color: string;
  cutout_url?: string | null;
  image_url?: string | null;
};
type Outfit = {
  name: string;
  items: Record<string, string>;
  reasons: string[];
  scores: Record<string, number>;
};
type WeatherInfo = {
  location?: string;
  feels_like?: number | null;
  condition?: string;
  humidity?: number | null;
  temperature_rule?: { label: string; advice: string };
};

export default function Home() {
  const [city, setCity] = useState("北京");
  const [weather, setWeather] = useState<WeatherInfo | null>(null);
  const [garments, setGarments] = useState<Garment[]>([]);
  const [outfits, setOutfits] = useState<Outfit[]>([]);
  const [outfitId, setOutfitId] = useState<number | null>(null);
  const [active, setActive] = useState(0);
  const [generating, setGenerating] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [error, setError] = useState("");

  const today = new Date();
  const dateStr = `${today.getMonth() + 1}月${today.getDate()}日`;
  const weekStr = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"][today.getDay()];

  useEffect(() => {
    fetch(`${API_PREFIX}/garments`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setGarments)
      .catch(() => {});
    fetch(`${API_PREFIX}/weather?location=${encodeURIComponent(city)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setWeather(d))
      .catch(() => {});
  }, [city]);

  function imageFor(name?: string) {
    if (!name) return null;
    const g = garments.find((x) => x.name === name);
    return assetUrl(g?.cutout_url || g?.image_url || null);
  }

  async function generate() {
    setGenerating(true);
    setError("");
    setStreamText("");
    setOutfits([]);
    try {
      const res = await fetch(`${API_PREFIX}/outfits`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scene: "日常", location: city }),
      });
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop()!;
        for (const part of parts) {
          let ev = "message";
          let data = "";
          for (const line of part.split("\n")) {
            if (line.startsWith("event:")) ev = line.slice(6).trim();
            else if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (!data) continue;
          const obj = JSON.parse(data);
          if (ev === "chunk") setStreamText(obj.text);
          else if (ev === "done") {
            setOutfits(obj.outfits ?? []);
            setOutfitId(obj.outfit_id);
            if (obj.weather) setWeather(obj.weather);
            setActive(0);
          } else if (ev === "error") setError(obj.error?.message ?? "生成失败");
        }
      }
    } catch {
      setError("生成失败，请重试");
    } finally {
      setGenerating(false);
    }
  }

  async function favorite() {
    if (outfitId == null) return;
    await fetch(`${API_PREFIX}/outfits/${outfitId}/favorite`, { method: "POST" });
  }

  const current = outfits[active];
  const itemEntries = current ? Object.entries(current.items) : [];

  return (
    <div className="mx-auto max-w-6xl">
      {/* 顶栏 */}
      <header className="flex items-end justify-between">
        <div>
          <h1 className="font-serif text-3xl text-ink-1">
            {dateStr} <span className="text-lg">{weekStr}</span>
          </h1>
          <p className="mt-1 text-sm text-ink-2">今日穿搭</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right text-sm">
            {weather?.condition ? (
              <>
                <span className="font-medium text-ink-1">
                  {weather.feels_like != null ? `${Math.round(weather.feels_like)}°` : "—"} {weather.condition}
                </span>
                {weather.temperature_rule && (
                  <span className="ml-2 rounded-full bg-violet-50 px-2 py-0.5 text-xs text-violet-800">
                    {weather.temperature_rule.label}
                  </span>
                )}
              </>
            ) : (
              <span className="text-ink-2">天气加载中…</span>
            )}
          </div>
          <input
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="城市，如 北京"
            className="w-36 rounded-full border border-bone-2 bg-white px-4 py-2 text-sm outline-none focus:border-violet-400"
          />
          <button
            onClick={generate}
            disabled={generating}
            className="grad-violet rounded-full px-5 py-2 text-sm font-medium text-white shadow-sm disabled:opacity-50"
          >
            {generating ? "生成中…" : "生成穿搭"}
          </button>
        </div>
      </header>

      {error && <p className="mt-3 text-sm text-err">{error}</p>}

      {/* 内容区 */}
      {generating ? (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          <div className="grad-aurora flex h-[420px] items-center justify-center rounded-lg">
            <div className="skel h-[400px] w-full rounded-md" />
          </div>
          <div className="grad-card rounded-lg p-5 text-sm text-violet-800">
            <p className="font-medium">正在为你生成</p>
            <p className="mt-2 text-[13px] text-violet-800/80">{streamText || "读取衣柜…"}</p>
          </div>
        </div>
      ) : current ? (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px]">
          {/* 左：主视觉 */}
          <div className="grad-aurora relative rounded-lg p-4">
            <div className="grid grid-cols-2 gap-3">
              {itemEntries.map(([cat, name]) => {
                const img = imageFor(name);
                return (
                  <div key={cat} className="flex flex-col items-center justify-center rounded-sm bg-white/85 p-4">
                    {img ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={img} alt={name} className="h-56 w-full rounded-xs object-contain" />
                    ) : (
                      <div className="flex h-56 w-full items-center justify-center">
                        <span className="font-serif text-xl text-bone-3">{name}</span>
                      </div>
                    )}
                    <p className="mt-3 text-sm text-ink-2">
                      {cat} · {name}
                    </p>
                  </div>
                );
              })}
            </div>
            <span className="grad-violet absolute left-6 top-6 rounded-full px-3 py-1 text-xs text-white">
              AI 生成
            </span>
          </div>

          {/* 右：方案详情 */}
          <div className="flex flex-col card-soft rounded-lg bg-white p-5 ring-1 ring-bone-2">
            <h2 className="font-serif text-2xl leading-tight text-ink-1">{current.name}</h2>
            <p className="mt-2 text-sm text-ink-2">
              {itemEntries.map(([k, v]) => `${k}·${v}`).join("　")}
            </p>

            {/* 三套切换 */}
            {outfits.length > 1 && (
              <div className="mt-4 flex gap-2">
                {outfits.map((o, i) => (
                  <button
                    key={i}
                    onClick={() => setActive(i)}
                    className={`h-9 flex-1 rounded-full text-xs transition-colors ${
                      i === active ? "grad-violet text-white" : "bg-bone-1 text-ink-2"
                    }`}
                  >
                    方案 {i + 1}
                  </button>
                ))}
              </div>
            )}

            {/* 理由 */}
            {current.reasons?.length > 0 && (
              <div className="mt-4 space-y-1.5 text-sm text-ink-2">
                {current.reasons.map((r, i) => (
                  <p key={i}>· {r}</p>
                ))}
              </div>
            )}

            {/* 匹配分 */}
            {current.scores && Object.keys(current.scores).length > 0 && (
              <div className="mt-4 grid grid-cols-2 gap-2">
                {Object.entries(current.scores).map(([k, v]) => (
                  <div key={k} className="rounded-md bg-bone-1 px-3 py-2 text-center">
                    <p className="text-xs text-ink-2">{k}</p>
                    <p className="text-lg font-medium text-ink-1">{v}</p>
                  </div>
                ))}
              </div>
            )}

            {/* 操作 */}
            <div className="mt-auto flex gap-2 pt-5">
              <button
                onClick={favorite}
                className="grad-terra flex-1 rounded-full py-2.5 text-sm font-medium text-white shadow-sm"
              >
                存入今日
              </button>
              <button
                onClick={() => setActive((active + 1) % outfits.length)}
                className="flex-1 rounded-full border border-bone-2 py-2.5 text-sm text-ink-1"
              >
                换一套
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="grad-aurora mt-6 rounded-lg p-16 text-center">
          <div className="grad-violet mx-auto flex h-24 w-24 items-center justify-center rounded-full text-4xl text-white shadow-sm">
            衣
          </div>
          <p className="mt-5 text-lg text-ink-1">今天穿什么？</p>
          <p className="mt-1 text-sm text-ink-2">
            填好城市，点右上角「生成穿搭」，AI 从你的衣柜里搭一套
          </p>
          <button
            onClick={generate}
            className="grad-terra mt-6 rounded-full px-8 py-3 text-sm font-medium text-white shadow-sm"
          >
            生成第一套
          </button>
        </div>
      )}
    </div>
  );
}
