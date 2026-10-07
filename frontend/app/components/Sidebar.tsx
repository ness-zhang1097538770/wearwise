"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { CalendarDays, Shirt, Sparkles, UserRound, ScanSearch } from "lucide-react";
import CatMascot from "./CatMascot";

const NAV = [
  { href: "/", label: "今日穿搭", Icon: CalendarDays },
  { href: "/wardrobe", label: "我的衣橱", Icon: Shirt },
  { href: "/tryon", label: "AI 试穿", Icon: Sparkles },
  { href: "/analysis", label: "购物分析", Icon: ScanSearch },
  { href: "/me", label: "我的", Icon: UserRound },
];

export default function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-56 flex-none flex-col border-r border-bone-2 bg-white/70 px-4 py-6">
      <Link href="/" className="px-2">
        <span className="grad-text font-serif text-2xl">WearWise</span>
        <span className="mt-1 block text-xs text-ink-2">AI 穿搭 · 理性购物</span>
      </Link>

      <nav className="mt-8 flex flex-col gap-1">
        {NAV.map(({ href, label, Icon }) => {
          const on = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-full px-3 py-2.5 text-sm transition-all ${
                on
                  ? "grad-violet font-medium text-white shadow-md"
                  : "text-ink-2 hover:bg-bone-1 hover:text-ink-1"
              }`}
            >
              <Icon size={18} strokeWidth={on ? 2 : 1.6} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* 左下角小猫 IP */}
      <div className="mt-auto flex flex-col items-center pt-4">
        <CatMascot />
      </div>
    </aside>
  );
}
