# CPBL ATLAS V0.4 — 即時戰況 / 文字轉播

本功能為**官方來源的準即時文字戰況快照**，不是 CPBL 官方服務或授權影音轉播。GitHub Pages 是靜態網站，無法從瀏覽器直接向中職站台 POST 並獲得同源的逐球即時資訊；因此使用定時 GitHub Actions 更新靜態 JSON、前端每 60 秒檢查有無更新的資料，並提供進入 CPBL **官方真正即時文字轉播**的按鈕。

## 預期內容

- 比賽日期、球隊、正式場次編號、狀態、R/H/E、逐局比分。
- **有原始記錄才顯示**目前 B/S/O、壘包、投手、打者與最近逐打席文字紀錄。事件篩選：全部、得分、安打、保送、全壘打。
- 比賽時段 Actions 預計每 5 分鐘執行，離峰時段每約 30 分鐘執行；GitHub 不保證準時開始或成功。網站每分鐘讀取更新快照；超過 15 分鐘的快照顯示「資料已過期」。這**不是秒級直播**。
- `data/live/YYYY-MM-DD.json` 對應歷史日期；`data/live/latest.json` 保留最新成功資料。官方資料抓取失敗時絕不將錯誤字串當比分，亦不覆蓋上次成功資料。
- 為尊重官方資料權利、站台安全與負載，本程式不繞過封鎖或 DRM，不嵌入或轉傳比賽影音。請先確認 CPBL 的資料使用規範及允許的抓取頻率。正式即時影片請使用官方平台或合法轉播商。

## 在你已建立的 Repository 安裝

目標：`https://github.com/chen10eason-png/cpbl-atlas`，並保留既有資料和原有統計頁。

1. 解壓 `cpbl-atlas-v0.4.0.zip`，把 `cpbl-atlas` 資料夾中的**所有內容**放到儲存庫根目錄，不是另加一層資料夾。包含 `assets/live.js`、更新後的 `assets/app.js`/`style.css`/`index.html`、`scripts/sync_live.py`、`tests`、以及隱藏的 `.github/workflows/live.yml`、`.github/workflows/website.yml`。
2. 若 GitHub 網頁上傳無法選到隱藏的 `.github`，用 **Add file → Create new file** 建立完整路徑 `.github/workflows/live.yml`，貼入壓縮檔內 `live.yml` 的內容。`website.yml` 同樣照做，因為你之前的 Repo 未出現 `.github/workflows`，會導致同步一直未啟動。
3. 開啟 **Settings → Pages → Build and deployment → Source: GitHub Actions**；在 **Settings → Actions → General → Workflow permissions** 確保 Actions 擁有讀寫內容所需權限；若帳號或組織政策禁止寫入，改用受許可的資料儲存方式，不應嘗試繞過。
4. 先到 **Actions → Build and update CPBL Atlas → Run workflow**（處理歷史年份快照與重新發佈）。等工作結束，再到 **Actions → CPBL Atlas - Scheduled Live Gamecast → Run workflow**。
5. 看執行紀錄：如果 `Fetch CPBL games and validate snapshot` 出現 403、驗證 token 缺失、JSON 格式錯誤等，代表官方資料同步仍未通過，**不能聲稱已上線即時比分**。從 [CPBL 官方網站](https://www.cpbl.com.tw/schedule) 開啟實際轉播仍可使用。修正前不得以虛構的範例資料替代。
6. 成功時確認 Repository 出現 `data/live/YYYY-MM-DD.json`，其中 `games` 不是範例數字且 `updatedAt` 為本次執行時間；開啟 `https://chen10eason-png.github.io/cpbl-atlas/#live`，檢查日期、比分與官方連結。

> Repository 目前被目前連線的 GitHub 帳號授予**只讀**權限，無法代你合併部署。上述是實際需要的操作，非宣稱已自動上線。

## 資料來源、資格和限制

- 比賽清單：`https://www.cpbl.com.tw/schedule` + `/home/getdetaillist`（CSRF token）。
- 單場資料：`https://www.cpbl.com.tw/box/live?gameSno=...&kindCode=...&year=...` + `/box/getlive`，`GameDetailJson`/`ScoreboardJson`/`LiveLogJson`。
- 以上端點由公開資料與第三方程式碼研究得知；**尚未在 GitHub Actions 實際驗證 2026/10/19 當日回應**。官方可能改版、限制自動存取或拒絕雲端 IP。
- 按中職聯盟文字轉播呈現的資料順序與原始欄位辨識，不代表中職對第三方提供資料服務之承諾。若單場逐球明細失敗，僅顯示可用的場次／比分並保留「官方查看」按鈕。

## 測試

```shell
python -m pip install -r requirements-sync.txt
python -m unittest discover -s tests -v
npm test
# 真的要聯網同步，需於可連官方網站且允許抓取的環境：
python scripts/sync_live.py
```

測試使用**模擬測試資料**，只用於驗證格式、安全跳脫、站台完整性；發布 ZIP **沒有**捏造 `data/live/*.json` 檔案。
