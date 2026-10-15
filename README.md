# SplitMate

SplitMate 是一個多人分帳網站。你可以建立分帳活動（例如聚餐或旅行）、加入成員、依分類記錄共同支出；系統會自動計算每個人的應收或應付金額、提供建議的付款方式，並追蹤每筆建議款項的付款狀態。

## 使用流程

1. 在首頁查看既有活動，或前往「建立新活動」。
2. 輸入活動名稱並加入至少兩位成員。
3. 在活動明細頁查看成員、總支出與每筆支出。
4. 新增支出，選擇分類、付款者及分攤成員；可平均分攤，或輸入每位成員的自訂金額（加總須等於支出金額）。
5. 開啟分帳結果，查看每位成員的應收／應付餘額與建議付款方式。
6. 將建議款項標記為「已付款」或取消付款標記；狀態會儲存在資料庫並於重新整理後保留。

所有金額均以 `Decimal` 與整數分進行計算；無法整除的零錢會用固定順序分配。

## 專案結構

| 路徑 | 用途 |
| --- | --- |
| `config/` | Django 專案設定與根路由 |
| `expenses/` | 分帳模型、表單、服務、頁面與測試 |
| `expenses/migrations/` | 資料庫結構遷移 |
| `expenses/static/` | CSS 與 JavaScript |
| `expenses/templates/` | 活動、支出與分帳頁面 |
| `expenses/tests/` | Django 自動化測試 |
| `locale/` | 英文翻譯目錄與編譯檔 |
| `scripts/` | 專案維護腳本 |
| `templates/` | 共用模板 |
| `manage.py` | Django 管理指令入口 |
| `requirements.txt` | Python 套件相依清單 |

## 系統需求

- Python 3.10 或更新版本
- Windows PowerShell（下方指令以 Windows 為例）

## 本機安裝

```powershell
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
python manage.py migrate
```

SplitMate 使用專案目錄中的 SQLite 資料庫 `db.sqlite3`，不需要另外安裝資料庫服務。

## 執行與測試

啟動開發伺服器：

```powershell
python manage.py runserver 8500
```

啟動成功後，在瀏覽器開啟 http://127.0.0.1:8500/

右上角的 `EN`／`中文` 按鈕可切換整個網站的語言，預設為繁體中文。

執行完整測試：

```powershell
python manage.py test
```

檢查 Django 設定與 migration 狀態：

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
```

## 目前功能與未來擴充

SplitMate 未來可發展為結合「多人分帳」與「個人記帳」的財務工具。以下模組為產品功能的劃分與發展方向。

### 分帳模組（目前已有）

- 建立活動並管理參與成員
- 記錄共同支出、付款者與分攤成員
- 使用平均分攤或自訂金額分攤
- 將支出分類為餐飲、住宿、交通、活動、購物或其他
- 計算每位成員的應付、應收與建議付款方式
- 將建議款項標記為未付款或已付款，並持久化保存狀態

### 個人記帳模組（未來擴充）

- 記錄個人收入與支出
- 管理現金、銀行帳戶與電子錢包
- 設定固定收入、固定支出與週期性交易
- 設定每月或各分類的預算
- 查看月報、收支趨勢與分類統計

### 兩個模組的整合方向

- 將共同支出選擇性同步至個人帳本，區分自己的負擔與替他人代墊的金額
- 完成分帳付款時，自動記錄對應的轉入或轉出
- 在整合首頁同時查看個人收支、待收款、待付款與近期活動
- 共用分類資料，讓個人記帳與多人分帳的統計保持一致

### 其他可延伸能力

- 使用者登入、個人工作區與資料權限
- 多人即時協作與付款提醒
- 收據 OCR 與快速建立支出
- 多幣別、匯率換算與旅行帳本
- CSV 或 PDF 匯出與備份
