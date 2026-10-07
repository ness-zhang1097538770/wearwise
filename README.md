# WearWise（穿衣助手）

![状态](https://img.shields.io/badge/%E7%8A%B6%E6%80%81-%E5%90%8E%E7%AB%AF%20MVP%20%E5%B7%B2%E5%AE%8C%E6%88%90-2ea44f?style=flat)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16-000000?style=flat&logo=nextdotjs&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?style=flat&logo=tailwindcss&logoColor=white)
![Doubao](https://img.shields.io/badge/Doubao-4E7FFF?style=flat)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat)

AI 穿搭与理性购物助手。本仓库是 WearWise 项目的代码与文档（多项目仓库中的独立项目文件夹）。

## 当前进度

- 阶段 2 后端 MVP 三个子阶段（2.1 衣柜与穿搭 / 2.2 Avatar+上身图 / 2.3 视频+购物分析）已完成，真实模型冒烟全通。
- 已打通完整主链路：录衣柜 → 穿搭 → 平铺图 → Avatar → 上身图 → 试穿视频 → 购物分析。
- 下一步：阶段 3 正式前端（Next.js），或先由产品经理验收后端 MVP。

## 目录结构

```
wearwise穿衣助手/
├── PRD/PRD.md            # 产品需求文档 V2.0
├── 项目状态.md            # 进度与决策台账
├── 阶段文档/              # 技术适配声明、分阶段开发文档、PRD 补全清单
├── evidence/             # 各阶段证据包
├── backend/              # FastAPI 后端（含最小验收界面）
│   ├── app/
│   ├── tests/
│   └── requirements.txt
└── data/                 # 本地数据库/图片（gitignored，运行时生成）
```

## 启动方法

### 后端（端口 8001）

```bash
cd docs/wearwise穿衣助手/backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
```

### 前端（端口 3001，避开其他项目占用的 3000）

```bash
cd docs/wearwise穿衣助手/frontend
npm install   # 首次
npm run dev   # 默认 3000，被占用时自动切到 3001
```

打开前端：http://127.0.0.1:3001/

## 验证方法（照着点）

1. 打开 http://127.0.0.1:8001/ ，选择一张衣服照片点"上传并识别"；
2. 看到识别出的标签，可修改后点"确认/保存"；
3. 录 2–3 件后，在右侧填场合/天气点"生成穿搭（流式）"；
4. 看到 3 套文字方案（流式出现）；
5. 点其中一套"生成平铺图"，等待出图（无 Key 时为占位图）；
6. 点"收藏"，刷新后仍在。

## 自动化测试

```bash
cd docs/wearwise穿衣助手/backend
.venv/bin/python -m pytest tests/ -q
```

## 接口

- `POST /api/v1/garments` 上传衣物照片 + 识别
- `GET /api/v1/garments` 衣物列表
- `PATCH /api/v1/garments/{id}` 修正标签
- `DELETE /api/v1/garments/{id}` 删除
- `POST /api/v1/outfits` 生成穿搭（SSE：chunk → done）
- `POST /api/v1/outfits/{id}/items/{idx}/image` 平铺图（提交+轮询）
- `GET /api/v1/tasks/{id}` 任务状态
- `POST /api/v1/outfits/{id}/favorite` 收藏

错误统一返回 `{"error":{"code","message"}}`。

## 说明

- 模型走火山方舟，`TEXT_MODEL`/`VISION_MODEL`/`IMAGE_MODEL` 需填**推理接入点 ID**（`ep-` 开头），不是模型名。
- 文字/识别用 Doubao-Seed-2.1-lite（已禁用深度思考，出结果快）；平铺图用 Doubao-Seedream-5.0-pro（需 1920×1920 以上）。
- 无火山方舟 Key 时自动走 mock（不调用真实模型），`MOCK_LLM=true` 可强制 mock。
- 数据存本地 SQLite（`data/wardrobe.db`），图片存 `data/uploads/`、`data/generated/`。
