# TransitFlow — 大眾運輸智慧查詢與管理系統

TransitFlow 是一個結合**大語言模型（LLM）Agent**、**關聯式資料庫（PostgreSQL）**與**圖形資料庫（Neo4j）**的大眾運輸智慧查詢系統。

> 📄 **完整版專題報告**：請參閱 [專題報告.md](專題報告.md) 了解系統設計理念、架構重構的詳細技術細節與量化效益評估。本文件僅涵蓋快速啟動指南。

本專案透過完全容器化的微服務架構，實作了基於 RAG 的政策問答、基於 Graph 的最短/最廉路徑分析、以及基於 Celery 的非同步排程任務。

## 核心特色

1. **AI Agent 推論管線**：以 `llama3.2:1b` 為核心，自動解析使用者意圖並路由至對應的資料庫查詢工具。
2. **多資料庫混合架構**：
   - **PostgreSQL**: 儲存使用者、票務交易，並透過 `pgvector` 進行政策文件的向量相似度搜尋。
   - **Neo4j**: 建立站點與路線的網路拓撲，透過 APOC 庫計算 Dijkstra 最短路徑與延誤漣波分析。
   - **Redis**: 雙軌運行，DB 0 作為 Dashboard 聚合查詢的毫秒級快取（實測 5.5 倍加速），DB 1/2 作為 Celery 任務的 Broker 與 Backend。
3. **雲端原生與容器化 (Twelve-Factor App)**：
   - 全服務 Docker 化（Python UI, DBs, Celery, Ollama）。
   - 環境分離架構：透過 `docker-compose.yml` 搭配 `.dev.yml` / `.prod.yml` 區分開發與正式環境。
   - 內建 `condition: service_healthy` 健康檢查確保啟動順序無依賴死鎖。

## 快速啟動

本專案已完成全自動化腳本綁定，只需安裝 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 即可一鍵啟動，**無需在本機安裝任何 Python 環境或資料庫**。

### 1. 複製專案

```bash
git clone https://github.com/your-username/Linux_final.git
cd Linux_final
```

### 2. (選用) 建立本地 Python 虛擬環境

雖然系統完全由 Docker 執行，但為了讓 VS Code 等編輯器能提供程式碼自動補全與語法檢查，建議在本地建立虛擬環境：

```bash
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 啟動系統（開發環境模式）

```bash
# 啟動所有容器（包含自動下載 Ollama 模型與寫入種子資料）
docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file .env.dev up -d
```

*💡 系統首次啟動時，`init-db` 容器會自動建立資料表、建立 Graph 節點並下載 LLM 模型，大約需要 1~3 分鐘。*

### 4. 開啟系統

待容器全數啟動完畢後，開啟瀏覽器瀏覽：

- **使用者與管理員介面 (UI)**: [http://localhost:7860](http://localhost:7860)
- **PostgreSQL 管理 (pgAdmin)**: [http://localhost:5051](http://localhost:5051) (帳號：admin@transitflow.com / 密碼：admin)
- **Neo4j 圖形化介面**: [http://localhost:7474](http://localhost:7474)

#### 預設測試帳號與權限功能

系統初始化時已建立以下三種權限的測試帳號（密碼皆有區分大小寫）。登入後除了能使用專屬的 Dashboard 外，也能透過自然語言請 AI 執行特定權限的任務：

- **管理員 (Admin)**

  - 帳號：`alice.tan@email.com` / 密碼：`alice1990`
  - **專屬功能**：可查看全系統營收與訂單統計、活躍用戶排行，並可指派 AI 執行背景排程任務（例如輸入：「幫我清理 30 天前的舊 Session」），並在「Task Progress」面板追蹤 Celery 執行進度。
- **員工 (Employee)**

  - 帳號：`ben.lim@email.com` / 密碼：`BenLim85`
  - **專屬功能**：可查看今日營運報表（Today's Operations Summary）與各路線即時載客率。
- **一般乘客 (Passenger)**

  - 帳號：`clara.wong@email.com` / 密碼：`clara08nov`
  - **專屬功能**：可透過 AI 查詢最短/最廉路線（Graph DB）、詢問退換票政策（Vector DB RAG），以及進行訂票操作。

## 測試與驗證

本專案內建 Smoke Test（冒煙測試）腳本，可自動驗證各微服務連線與 Agent 功能：

```bash
docker compose run --rm ui python scripts/smoke_test.py
```

## 服務與架構配置說明

| 服務容器        | 說明                             | 內部 Port |
| --------------- | -------------------------------- | --------- |
| `ui`          | Gradio 前端與 LLM Agent 核心邏輯 | 7860      |
| `ollama`      | 本地端 LLM 引擎 (llama3.2:1b)    | 11434     |
| `postgres`    | 關聯式資料庫與向量庫 (pgvector)  | 5432      |
| `neo4j`       | 圖形資料庫 (APOC)                | 7687      |
| `redis`       | 快取與 Celery Broker             | 6379      |
| `celery`      | 非同步任務執行器 (Worker)        | -         |
| `celery-beat` | 排程任務發布器 (Cron Jobs)       | -         |
