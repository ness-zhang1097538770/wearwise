"use client";

import { useEffect, useState } from "react";
import { API_PREFIX, assetUrl } from "../lib/api";

type Avatar = { id: number; candidates: { index: number; image_url: string }[]; selected: number | null; is_primary: boolean };

export default function Me() {
  const [avatar, setAvatar] = useState<Avatar | null>(null);
  const [garmentCount, setGarmentCount] = useState(0);

  useEffect(() => {
    fetch(`${API_PREFIX}/avatars`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list: Avatar[]) => setAvatar(list.find((a) => a.is_primary) ?? null))
      .catch(() => {});
    fetch(`${API_PREFIX}/garments`)
      .then((r) => (r.ok ? r.json() : []))
      .then((list: unknown[]) => setGarmentCount(list.length))
      .catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="font-serif text-3xl text-ink-1">我的</h1>
      <p className="mt-1 text-sm text-ink-2">数字形象、衣柜与设置</p>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* 主形象 */}
        <section className="card-soft rounded-lg bg-white p-5 ring-1 ring-bone-2">
          <h2 className="text-base font-medium text-ink-1">我的数字形象</h2>
          {avatar && avatar.selected != null ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={assetUrl(avatar.candidates[avatar.selected]?.image_url)}
              alt="主形象"
              className="mt-3 h-56 rounded-sm object-contain"
            />
          ) : (
            <p className="mt-3 text-sm text-ink-2">还没有主形象，去「AI 试穿」页生成一个吧</p>
          )}
        </section>

        {/* 统计 + 关于 */}
        <section className="flex flex-col gap-6">
          <div className="card-soft rounded-lg bg-white p-5 ring-1 ring-bone-2">
            <h2 className="text-base font-medium text-ink-1">我的衣柜</h2>
            <p className="mt-2 text-3xl font-medium text-ink-1">{garmentCount} <span className="text-base text-ink-2">件衣物</span></p>
            <p className="mt-1 text-sm text-ink-2">去「我的衣橱」页管理你的衣物</p>
          </div>

          <div className="grad-card rounded-lg p-5">
            <h2 className="text-base font-medium text-ink-1">关于 WearWise</h2>
            <p className="mt-2 text-sm text-ink-2">
              AI 穿搭与理性购物助手：先用好已有衣物，再决定是否购买新衣。
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
