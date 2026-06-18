# Task 6 — Bonus 實作計畫

> 本文件依據 `grading_student/STUDENT_GUIDE_CODE.md`、`STUDENT_GUIDE_DOC.md`、`STUDENT_GUIDE_LIVE.md` 整理。
> 所有評分標準皆以上述文件為準，本文件僅作為分工參考。

---

## 建議的撰寫時機與順序

根據 `STUDENT_GUIDE_CODE.md` 的提醒：

> Without `TASK6.md` and the per-file comment markers, the bonus section will not be graded.

以及 `STUDENT_GUIDE_DOC.md` 的說明：

> If Section 7 is present but the code does not include `TASK6.md` or per-file comment markers, the live and code bonus sections will not be awarded — only this document bonus can be graded.

由此得出以下結論：

### 建議流程

```
開發中（每改一個檔案）
  └─ 立刻在該檔案頂部加上 # TASK 6 EXTENSION: 註解

開發中（每寫一個新函數）
  └─ 立刻補上詳細 inline 註解（說明 why）

兩個 branch 都開發完、merge 回 main 之後
  ├─ 建立 TASK6.md（統一登記所有修改檔案、函數名、資料表名）
  └─ 撰寫設計文件 Section 7（截圖、範例 query 輸出在此時補齊）
```

### 理由

| 項目 | 時機 | 原因 |
|------|------|------|
| `# TASK 6 EXTENSION:` 檔案頂部註解 | **開發時立刻加** | 容易忘記；且沒有這個標記，TA 不會評 code/live bonus |
| 函數 inline 註解（why 型） | **寫函數時一起寫** | 事後補容易遺漏；這是 code bonus +3 分的直接來源 |
| `TASK6.md` | **全部 merge 完後建立** | 需要列出所有檔案與函數，merge 完才能確認完整清單 |
| 設計文件 Section 7 | **全部 merge 完後撰寫** | 需要測試截圖與實際 query 輸出，必須等程式跑起來後才能取得 |

**不需要事先建立任何記錄檔**，只要開發時每個檔案頂部加上 `# TASK 6 EXTENSION:` 即可，`TASK6.md` 和 Section 7 留到最後統一完成。

---

## Branch 命名規範

| Branch | 用途 |
|--------|------|
| `feature/task6-relational` | PostgreSQL 新增 schema、query 函數、seed data |
| `feature/task6-graph` | Neo4j 新增 Cypher query 函數、seed data |

兩個 branch 從最新的 `main` 建立，開發完成後依序 merge 回 `main`（先 merge 其中一個，另一個 rebase 後再 merge）。

---

## 共同必要條件（兩個 branch 都需配合完成）

根據 `STUDENT_GUIDE_CODE.md` Task 6，以下四項缺一不可，否則 bonus **不予評分**：

1. 擴充內容必須觸及資料庫程式碼（新 schema、queries 或 seed data）
2. 每個新的資料庫操作都要有詳細 inline 註解，說明 **why**，不只是 what
3. 設計文件中要有 **Section 7**（動機、schema 變更、範例 query、測試截圖）
4. Repo 根目錄要有 **`TASK6.md`**，列出所有被修改或新增的檔案、具體函數名與資料表名；每個被修改的檔案頂部要有 `# TASK 6 EXTENSION:` 註解

> **重要提醒（來自 STUDENT_GUIDE_CODE.md）：**
> Without `TASK6.md` and the per-file comment markers, the bonus section will not be graded.

---

## Branch 1：`feature/task6-relational`

### 修改的檔案

- `databases/relational/schema.sql`
- `databases/relational/queries.py`
- `skeleton/seed_postgres.py`

### 要做的事

> **注意**：`execute_cancellation`（含退款計算）已是 `STUDENT_GUIDE_CODE.md` Task 2 Write operations 與 `STUDENT_GUIDE_LIVE.md` B10 的**必做函數**，不計入 Task 6 bonus。
> Task 6 bonus 只計算在 Task 1–5 範圍之外、全新新增的 schema、query 或 seed data。

#### 1. 使用者旅行歷史 — `query_user_travel_history`（新函數，不在 Task 1–5 範圍內）

- 在 `databases/relational/queries.py` 新增函數 `query_user_travel_history(user_email)`
- 整合 `national_rail_bookings` 與 `metro_bookings`，回傳使用者所有已完成的行程
- 每筆記錄包含：booking_id、路線、票種、票價、出發日期、狀態
- 回傳格式：`{"national_rail": [...], "metro": [...]}`（兩個 key 永遠存在）
- 此函數**未出現在** Task 2 的必要函數清單中，符合 Task 6 「new query function」資格

#### 2. 乘客統計 / 熱門路線 — `query_route_statistics`（新函數，不在 Task 1–5 範圍內）

- 在 `databases/relational/queries.py` 新增函數 `query_route_statistics()`
- 從 `national_rail_bookings` 與 `metro_bookings` 聚合出最熱門的起訖站對、各路線總搭乘人次
- 回傳格式：`{"top_routes": [...], "total_bookings_by_line": [...]}`
- 此函數**未出現在** Task 2 的必要函數清單中，符合 Task 6 「new query function」資格

#### 3. Schema 新增（若新函數需要新表）

來源：`STUDENT_GUIDE_CODE.md` Task 1

- 若新增統計或歷史功能需要獨立資料表，在 `databases/relational/schema.sql` 新增
- 須符合 Task 1 標準：正確 PK/FK、data types、cascade behavior、soft delete 策略
- 須在 `skeleton/seed_postgres.py` 補上對應的 seed 函數，且使用 `ON CONFLICT DO NOTHING` 保持 idempotency

#### Task 6 Code Bonus 評分方式（來自 `STUDENT_GUIDE_CODE.md`）

> Task 6 的四個評分項目是針對**本 branch 所有新增內容整體評分**，不是一個函數對應一份分數。

| 評分項目 | 分數 | 說明 |
|---------|------|------|
| Extension touches database code | 2 | 新的 query 函數確實存在於資料庫層 |
| Feature is functional end-to-end | 5 | 功能可透過直接 DB query 或 chat UI 驗證正確輸出 |
| Quality of implementation | 5 | 正確 types、transaction scope、index |
| Code comments explain every new operation | 3 | 每個新函數都有 why 型 inline 註解 |

---

## Branch 2：`feature/task6-graph`

### 修改的檔案

- `databases/graph/queries.py`
- `databases/graph/seed.cypher`（或 `skeleton/seed_neo4j.py`）

### 要做的事

> **注意**：`query_delay_ripple` 已是 `STUDENT_GUIDE_CODE.md` Task 5 與 `STUDENT_GUIDE_LIVE.md` C5 的**必做函數**。
> Task 6 的資格條件要求「new」schema/queries/seed data——補齊既有必做函數**不計入 bonus**。
> `query_delay_ripple` 應確保正確實作以拿到 Task 5/C5 的基本分，不作為 bonus 項目。

#### 1. 路線可達性分析 — `query_reachable_stations`（新函數，不在 Task 1–5 範圍內）

來源：`STUDENT_GUIDE_CODE.md` Task 6 Extension 條件（new query functions）

- 在 `databases/graph/queries.py` 新增函數 `query_reachable_stations(origin_id, max_time_min)`
- 找出從指定站出發，在 `max_time_min` 分鐘內可到達的所有站點
- 使用 Cypher APOC `apoc.algo.dijkstra` 或 BFS/path expansion
- 每筆結果包含：station_id、name、total_time_min（從起點累計）
- 同時支援 metro 與 national rail 網路
- 此函數**未出現在** Task 5 的必要函數清單中，符合 Task 6 「new query function」資格

#### Task 6 Code Bonus 評分方式（來自 `STUDENT_GUIDE_CODE.md`）

> Task 6 的四個評分項目是針對**本 branch 所有新增內容整體評分**，不是一個函數對應一份分數。

| 評分項目 | 分數 | 說明 |
|---------|------|------|
| Extension touches database code | 2 | 新的 query 函數確實存在於資料庫層 |
| Feature is functional end-to-end | 5 | 功能可透過直接 DB query 或 chat UI 驗證正確輸出 |
| Quality of implementation | 5 | 正確 Cypher、indexed properties |
| Code comments explain every new operation | 3 | 每個新函數都有 why 型 inline 註解 |

#### 3. Seed Data 補強

來源：`STUDENT_GUIDE_CODE.md` Task 4、`STUDENT_GUIDE_LIVE.md` Section A

- 確認 `INTERCHANGE_TO` 關係已完整 seed（metro ↔ national rail 轉乘站）
- 確認所有 relationship 都有 `travel_time_min`、`cost_usd`（或 `cost_standard_usd`）屬性
- seed 必須使用 `MERGE` 而非 `CREATE`，保持 idempotency（`STUDENT_GUIDE_CODE.md` Task 3）

---

## Merge 順序建議

```
1. feature/task6-relational  →  merge 到 main（先）
2. feature/task6-graph       →  rebase 到最新 main，解決衝突後 merge
```

**可能衝突的共用檔案：**

| 檔案 | 衝突原因 | 處理方式 |
|------|---------|---------|
| `skeleton/agent.py` | 兩邊都可能新增 import 及 tool 定義 | 人工合併，各自只改自己的 import 區塊 |
| `TASK6.md` | 兩邊都需建立此檔 | 在第一個 branch 建立模板；第二個 branch rebase 後補自己的部分 |
| 設計文件 Section 7 | 同一份 `.md` | rebase 後統一撰寫，或最後由一人整合 |

---

## 設計文件 Section 7 需包含的內容

來源：`STUDENT_GUIDE_DOC.md` Task 6

| 項目 | 評分 | 說明 |
|------|------|------|
| Motivation — 說明為什麼此擴充有價值 | /3 | 具體論述，不能只說「增加功能」 |
| Database changes — 新 schema/Cypher，附 snippet | /4 | 實際的 SQL 或 Cypher，不能只有文字描述 |
| Example queries — 附預期輸出 | /4 | 至少一條完整 query + 實際輸出結果 |
| Testing evidence — 截圖或 pgAdmin/Neo4j Browser 輸出 | /4 | 證明實際執行並產生正確結果 |

---

## Live Demo 需準備的展示內容

來源：`STUDENT_GUIDE_LIVE.md` Task 6

| 展示項目 | 對應評分 |
|---------|---------|
| 在 Gradio UI 或直接 DB query 展示新功能正常運作 | /6 |
| 直接查詢資料庫確認資料正確（不只是不報錯） | /5 |
| 原有 B1–C6 測試項目全部正常，無 regression | /4 |
