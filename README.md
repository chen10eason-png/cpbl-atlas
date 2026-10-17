# CPBL ATLAS — 中華職棒歷年資訊及數據網站

> **專案初版／2026-10-17**。非中華職棒官方網站，也與野球革命無隸屬關係。介面採獨立設計。

## 網站有什麼

- **1990–2024 年**：有來源的歷年一軍例行賽打擊、投球、守備原始紀錄與球隊戰績（本版前端支援打者/投手榜、球隊戰績）。
- 依年度查詢、關鍵字搜尋、球隊篩選、欄位升降排序、每頁 30 位、CSV 下載。
- 依球員官方 ID 搜尋歷年生涯數據；同季跨隊合併顯示「多隊」，保留原始分隊紀錄。
- 打者 OPS / OBP / SLG / ISO / BABIP / K% / BB%；投手 ERA / WHIP / K9 / BB9。使用出局數而不是浮點小數計算 IP。
- 2025–2026 獨立使用官方 `RecordAllAction` 公開數值資料匯入，**僅在抓取及完整性檢查成功時才會出現在年分下拉**。
- 每日檢查來源、驗證後保存 JSON 快照、部署 GitHub Pages；官方來源失敗時不會覆蓋前次成功快照，並在 GitHub Actions 報告錯誤。

## 覆蓋與限制（必讀）

1. 已驗證可作為來源的開源資料集僅有 **1990–2024**。本工作環境無法對網際網路執行程式，所以第一版**尚未真的跑完全量擷取**。前端在 `data/YYYY.json` 不存在時會直接請求開源 CSV 並顯示；部署後 GitHub Actions 執行初次歷史資料同步。
2. `scripts/sync_official.py` 是依官方網站公開 Ajax 表單規則開發的**待線上實測連接器**；2025、2026 更新不能宣稱成功，直到 GitHub Action 成功寫出相應 `data/YYYY.json` 並驗證數量。
3. 球員進階 Trackman、投手球種、WAR、wRC+、UZR、Framing、WPA **尚未匯入**。2026 `stats.cpbl.com.tw` 僅含 2026 的進階資料，不能擅自把它當作 1990 年起皆存在的資料。
4. 2025–2026 官方補充資料若找不到正式 10 位數 ID，採年度限定替代 ID，避免跨年身份被誤合併。此限制會隨身份對照表成熟後改善。
5. 本版僅一軍例行賽。二軍、季後賽、總冠軍賽、球場校正及球隊跨年代改名鏈結都尚待擴充。
6. `data/` 不使用假資料；來源格式變動、403、欄位數異常時同步失敗並保留既存快照，不靜默寫零。

## 自動部署：推薦 GitHub Pages

1. 在 GitHub 建立新的 **public** Repository（例如 `cpbl-atlas`），預設分支 `main`。
2. 解壓縮本 ZIP，**完整上傳所有檔案及資料夾，包含 `.github/workflows/website.yml`**。
3. 在新 Repo **Settings → Pages → Build and deployment → Source** 選 `GitHub Actions`。
4. 至 **Actions → Build and update CPBL Atlas → Run workflow** 手動執行第一次同步。第一次要抓 35 年 × 3 類開源 CSV，可能較慢。
5. 查看每次同步紀錄和 `data/manifest.json` 的 `years` 以確認實際涵蓋年度。自此每天台灣時間約早上 08:15 執行自動更新（平台可能延後）。
6. 開啟 GitHub Pages 公布的網址。資料更新是在伺服器排程產生快照，非瀏覽器持續爬蟲。

### 本機啟動

```bash
python -m http.server 8000
# 瀏覽 http://localhost:8000
```

前端會在本機沒有 `data/YYYY.json` 時從 `ldkrsi/cpbl-opendata` 讀取資料，**需能連線到 GitHub**。

```bash
python -m unittest discover -s tests -v
pip install -r requirements-sync.txt
python scripts/sync.py             # 只下載缺少的 1990–2024 球季
python scripts/sync.py --full      # 從來源重新下載、驗證全部 35 季
python scripts/sync_official.py --year 2026
```

若官方來源連接器失敗，先查看 GitHub Actions 記錄並檢查官方網站資料結構；**不要為讓排程變綠而跳過缺頁驗證**。

## 資料來源與使用條件

- [ldkrsi/cpbl-opendata](https://github.com/ldkrsi/cpbl-opendata)：歷年（1990–2024）公開資料，MIT License，出處請保持標示；原資料整理自中職官網。年度球員 ID / 改名 / 轉隊可能有歷史誤差，見來源 README。
- [中華職棒官方](https://www.cpbl.com.tw/)：2025–2026 `recordall` / `teamrecord` 官方公示數值。自動擷取前仍需遵守官方服務條款、機器人規則、合理頻率，必要時取得授權。
- [中華職棒進階數據](https://stats.cpbl.com.tw/)：供 2026+ 進階項目後續對接研究；本版沒有批次複製此站的追蹤資料。
- [Rebas 野球革命 Open Data](https://github.com/rebas-tw/rebas.tw-open-data)：2023–2025 逐場公開資料，**ODC Attribution 1.0**，需要來源署名；本版未將其釋出的逐球數據匯入或聲稱已完整覆蓋。

## 目錄

```
index.html                       網站
assets/app.js, data.js, style.css  查詢與介面
scripts/sync.py                  1990–2024 原始紀錄匯入與驗證
scripts/sync_official.py         2025–2026 官方資料擷取（待正式實測）
.github/workflows/website.yml    每日抓取、驗證、GitHub Pages 發布
requirements-sync.txt            同步程式需要的依賴
tests/test_stats.py              數值計算、守門測試
data/                           經驗證後的 JSON 快照（初版為空）
```
