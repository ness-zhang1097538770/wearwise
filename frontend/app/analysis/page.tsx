"use client";

import { useRef, useState } from "react";
import { ScanSearch } from "lucide-react";
import { API_PREFIX } from "../lib/api";

type Report = {
  match_score?: number;
  match_reason?: string;
  duplicate_score?: number;
  duplicate_reason?: string;
  similar_items?: string[];
  can_pair_count?: number;
  pair_examples?: string[];
  cost_per_wear?: string;
  suggestion?: string;
  suggestion_reason?: string;
};
type Product = { name?: string; category?: string; color?: string; material?: string };

export default function Analysis() {
  const [analyzing, setAnalyzing] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [product, setProduct] = useState<Product | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [productImg, setProductImg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function analyze(file: File) {
    setAnalyzing(true);
    setStatusText("识别商品信息…");
    setReport(null);
    setProduct(null);
    setProductImg(URL.createObjectURL(file));

    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch(`${API_PREFIX}/analysis`, { method: "POST", body: fd });
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
        if (ev === "chunk") setStatusText(obj.text);
        else if (ev === "done") {
          setProduct(obj.product);
          setReport(obj.report);
        }
      }
    }
    setAnalyzing(false);
  }

  function suggestionColor(s?: string) {
    if (!s) return "text-ink-1";
    if (s.includes("值得考虑") || s.includes("先试穿")) return "text-ok";
    if (s.includes("重复") || s.includes("有限")) return "text-warn";
    if (s.includes("等待")) return "text-ink-2";
    return "text-ink-1";
  }

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="font-serif text-3xl text-ink-1">购物分析</h1>
      <p className="mt-1 text-sm text-ink-2">上传商品截图，判断它与你现有衣柜的匹配度、值不值得买</p>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[360px_1fr]">
        {/* 左：上传 */}
        <section className="card-soft rounded-lg bg-white p-5 ring-1 ring-bone-2">
          <button
            onClick={() => fileRef.current?.click()}
            disabled={analyzing}
            className="grad-aurora flex w-full flex-col items-center justify-center rounded-md border border-dashed border-violet-200 p-10"
          >
            <ScanSearch size={32} className="text-violet-600" />
            <p className="mt-3 text-sm text-ink-1">{analyzing ? statusText : "点击上传商品截图"}</p>
            <p className="mt-1 text-xs text-ink-2">支持 jpg / png / webp</p>
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && analyze(e.target.files[0])}
          />

          {productImg && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={productImg} alt="商品" className="mt-4 max-h-64 rounded-sm object-contain" />
          )}
        </section>

        {/* 右：报告 */}
        <section className="card-soft rounded-lg bg-white p-5 ring-1 ring-bone-2">
          {analyzing ? (
            <div className="grad-card rounded-md p-8 text-center text-sm text-violet-800">
              {statusText || "分析中…"}
            </div>
          ) : report ? (
            <div>
              {/* 商品信息 */}
              <div className="rounded-md bg-bone-1 p-4">
                <h2 className="text-base font-medium text-ink-1">{product?.name || "未知商品"}</h2>
                <p className="mt-1 text-sm text-ink-2">
                  {[product?.category, product?.color, product?.material].filter(Boolean).join(" · ") || "—"}
                </p>
              </div>

              {/* 核心指标 */}
              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-md bg-bone-1 p-4 text-center">
                  <p className="text-xs text-ink-2">衣柜匹配度</p>
                  <p className="mt-1 text-3xl font-medium text-ink-1">{report.match_score ?? 0}</p>
                  <p className="mt-1 text-xs text-ink-2">{report.match_reason || ""}</p>
                </div>
                <div className="rounded-md bg-bone-1 p-4 text-center">
                  <p className="text-xs text-ink-2">重复度</p>
                  <p className="mt-1 text-3xl font-medium text-ink-1">{report.duplicate_score ?? 0}</p>
                  <p className="mt-1 text-xs text-ink-2">{report.duplicate_reason || ""}</p>
                </div>
              </div>

              {/* 可搭配 */}
              <div className="mt-3 rounded-md bg-bone-1 p-4 text-sm text-ink-2">
                <p>
                  可搭配件数：<span className="font-medium text-ink-1">{report.can_pair_count ?? 0}</span>
                </p>
                {report.pair_examples?.length ? <p className="mt-1">{report.pair_examples.join("；")}</p> : null}
                {report.cost_per_wear ? (
                  <p className="mt-1">
                    单次穿着成本：<span className="font-medium text-ink-1">{report.cost_per_wear}</span>
                  </p>
                ) : null}
              </div>

              {/* 建议 */}
              <div className="mt-4 rounded-md grad-card p-4">
                <p className="text-sm">
                  建议：<span className={`font-medium ${suggestionColor(report.suggestion)}`}>{report.suggestion}</span>
                </p>
                {report.suggestion_reason && <p className="mt-1 text-[13px] text-ink-2">{report.suggestion_reason}</p>}
              </div>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-ink-2">
              上传商品图后，这里会显示分析报告
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
