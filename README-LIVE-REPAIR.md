# CPBL ATLAS 即時戰況 V0.4.1 修正

修正日：2026-10-20。這是對 `chen10eason-png/cpbl-atlas` 現有 V0.4 的增量修正。

## 找到的根因（真實 GitHub Actions 日誌）

- 2026-10-20 的 `CPBL Atlas - Scheduled Live Gamecast` 執行在 `scripts/sync_live.py` 的 `GET https://www.cpbl.com.tw/schedule` 回傳 HTTP 404；因此 `data/live/YYYY-MM-DD.json` 與 `latest.json` 沒有產生，網站顯示「沒有資料」。
- 歷史資料 `data/1990.json`—`data/2024.json` 存在，但 **即時戰況** 的 `data/live/` 完全沒有成功發布的日期快照。
- 原本的網站只會查當天 `data/live/YYYY-MM-DD.json`，沒有可供選取的歷史日期索引。

## 此修正內容

- 使用中職進階數據官網 `https://stats.cpbl.com.tw/api/proxy/v1/games/schedule` （`kindCode=A/C/E/D/F`）與 `GET /games/{年-類型-場次}`。這兩個端點的格式由公開專案交叉比對，**本環境尚不能向官網實際連線驗證**，務必看 Actions 日誌。
- 優先辨識 C（總冠軍賽）、E（季後挑戰賽），避免 10 月只查 A（例行賽）而漏比賽。
- 增加 `data/live/index.json` 歷史日期索引、過去 14 天初次回補、可手動回補 30 天及自選截至日。
- 即使某場明細失敗，只要官方月賽程已確認，仍保留場次；完整比分與逐球資料必須來自官方回應，未知數值顯示 `—`。
- 非法或無法取得賽程時 GitHub Actions 失敗且不發布新的空資料檔，避免誤寫成「沒有比賽」。
- 網頁新增「最近有比賽的日期」捷徑；資料不存在時明確說明「尚未同步」，而非「當日無賽事」。

## 上傳位置：務必保留路徑

**新的檔案**：
- `scripts/sync_live_stats.py`
- `tests/test_live_stats.py` （測試用，非必需但建議上傳）
- `README-LIVE-REPAIR.md` （這份說明）

**取代舊檔案**：
- `.github/workflows/live.yml`
- `.github/workflows/website.yml`
- `assets/live.js`
- `assets/style.css`
- `tests/live.mjs` （測試用，建議上傳）

只要上傳變更的這些檔案即可，不必覆蓋 `data/1990.json`—`data/2024.json`，也不必重建 Repo。

GitHub 上直接建立新檔：在專案根目錄使用 **Add file → Create new file**，輸入 `scripts/sync_live_stats.py`，貼上同名檔的內容提交；替換其他檔案時，點到原檔後按鉛筆編輯，將內容換成 ZIP 中對應檔案的內容。若透過資料夾拖放上傳，注意 `.github/workflows/` 是隱藏資料夾，確認資料夾結構有保留。

## 執行 / 驗收

1. GitHub → Actions → `CPBL Atlas - Scheduled Live Gamecast` → `Run workflow`。
2. `backfill_days` 選 14（可改 30），`target_date` 留空，執行。
3. **必須看到** `Fetching official CPBL stats API`、`PASS snapshots=14` 和 `HISTORICAL DAYS:`；若失敗，點 `Fetch official advanced-stats schedule and backfill history`，看是否 API 被擋或格式改變。
4. 成功後檢查 Repo 應產生 `data/live/index.json`、`data/live/latest.json`、`data/live/2026-10-20.json`，若前 14 天有賽事也會有對應日期 JSON。
5. 前往 https://chen10eason-png.github.io/cpbl-atlas/#live ，用「最近有比賽的日期」切換。若今天確實沒比賽，仍應能查看已存的歷史日期。

**注意**：只看到 GitHub Pages 綠色成功，不等於官方數據已取得；需實際看到 `data/live/index.json` 與各日期的場次，才算完成。若新的進階數據 API 也被 GitHub Actions 網路限制，本修正會明確失敗、保留舊資料；屆時需改用可取得官方資料的部署執行環境，而非繼續增加前端空畫面。

這是球賽文字即時戰況（定期快照），不是影片直播。GitHub Actions 排程可能延遲，不能保證逐秒同步。
