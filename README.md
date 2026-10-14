# SplitMate

SplitMate 是一個以 Django 建立的旅行分帳 MVP。你可以建立旅程與旅伴、記錄每筆共同支出，並取得精確到分的成員餘額與建議付款方式。

## 系統需求

- Python 3.10 或更新版本
- Windows PowerShell（下方指令以 Windows 為例）

## 本機安裝

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
```

SplitMate 使用專案目錄中的 SQLite 資料庫 `db.sqlite3`，不需要另外安裝資料庫服務。此檔案已被 Git 忽略。

## 執行與測試

啟動開發伺服器：

```powershell
python manage.py runserver
```

瀏覽器開啟 `http://127.0.0.1:8000/`。

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

## 使用流程

1. 在首頁查看既有旅程，或前往「建立新旅程」。
2. 輸入旅程名稱並加入至少兩位旅伴。
3. 在旅程明細頁查看成員、總支出與每筆支出。
4. 新增支出，選擇付款者及共同分攤的成員。
5. 開啟分帳結果，查看每位成員的應收／應付餘額與建議付款方式。

所有金額均以 `Decimal` 與整數分進行計算；無法整除的零錢會用固定順序分配，確保每一分都被保存。

## MVP 範圍

目前版本刻意不包含支出分類、付款完成狀態（例如 `payment_status` 或 `is_paid`）、登入與多人即時協作。這些功能可在核心分帳流程驗證完成後再擴充。
