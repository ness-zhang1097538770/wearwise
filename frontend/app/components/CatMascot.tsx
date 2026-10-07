"use client";

// WearWise 品牌小猫 IP（第一版：静态 3D 立绘 + 轻微浮动）
export default function CatMascot() {
  return (
    <div className="mt-auto flex flex-col items-center pt-6">
      <div className="cat-hop">
        <div className="relative h-32 w-32 overflow-hidden rounded-full ring-4 ring-bone-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/cat-ip/cat-front.jpg"
            alt="WearWise 小猫"
            className="h-full w-full object-cover"
          />
        </div>
      </div>
      <p className="mt-2 text-center text-xs text-ink-2">
        WearWise <span className="text-terra-600">喵</span>
      </p>
    </div>
  );
}
