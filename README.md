# SplitMate

SplitMate 是一個多人分帳網站。你可以建立分帳活動（例如聚餐或旅行）、加入成員並記錄共同支出；系統會自動計算每個人的應收或應付金額，並提供建議的付款方式。

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

## 使用流程

1. 在首頁查看既有活動，或前往「建立新活動」。
2. 輸入活動名稱並加入至少兩位成員。
3. 在活動明細頁查看成員、總支出與每筆支出。
4. 新增支出，選擇付款者及分攤成員；可平均分攤，或輸入每位成員的自訂金額（加總須等於支出金額）。
5. 開啟分帳結果，查看每位成員的應收／應付餘額與建議付款方式。

所有金額均以 `Decimal` 與整數分進行計算；無法整除的零錢會用固定順序分配。

## 專案結構

```text
SplitMate/
├── config/             # Django 專案設定與根路由
├── expenses/           # 分帳領域模型、表單、服務、頁面與測試
│   ├── migrations/     # 資料庫結構遷移
│   ├── static/         # CSS 與 JavaScript
│   ├── templates/      # 活動、支出與分帳頁面
│   └── tests/          # Django 自動化測試
├── locale/             # 英文翻譯目錄與編譯檔
├── scripts/            # 專案維護腳本
├── templates/          # 全站共用模板
├── manage.py
└── requirements.txt
```

## MVP 範圍

目前版本不包含支出分類、付款完成狀態、登入與多人即時協作。這些功能可在核心分帳流程驗證完成後再擴充。
