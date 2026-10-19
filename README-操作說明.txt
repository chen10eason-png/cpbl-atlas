CPBL ATLAS 2025 / 2026 資料缺漏修復
====================================================
確認狀態：2026-10-18
現有 Repo：https://github.com/chen10eason-png/cpbl-atlas
現有網站：https://chen10eason-png.github.io/cpbl-atlas/#overview

查核結果：
- GitHub main 分支已有 scripts/sync.py、sync_official.py、sync_halves.py。
- main 分支沒有 .github/workflows 資料夾，也沒有 data 資料夾。
- GitHub Pages 只有網站建置成功，沒有執行數據下載。

請在 repo 網頁照以下步驟操作（無需刪除既有檔案）：

第一步（最重要）：
  https://github.com/chen10eason-png/cpbl-atlas
  按 Add file → Create new file
  在檔名欄輸入：
  .github/workflows/website.yml
  將本壓縮檔裡的 .github/workflows/website.yml 全文貼入編輯框。
  直接 Commit changes 到 main。
  注意：不要只把 zip 檔上傳到 repo，GitHub 不會自動解壓。

第二步：
  開啟 Repo → Settings → Pages
  Build and deployment → Source → GitHub Actions。
  這是必要的，否則 deploy-pages 可能無法接手 Pages 部署。

第三步：
  開啟 Repo → Actions → CPBL Atlas - Sync 2025 2026 and Deploy
  選 Run workflow → main → Run workflow。

第四步：
  點開該次 Run → sync-and-deploy → Step:
  'Import CPBL 2025 and 2026 individually'
  確認 2025、2026 是否分別 PASS；若不是，保留該步完整錯誤日誌。
  再檢查 'Check published year list and basic statistical integrity'。

第五步（驗收）：
  成功後瀏覽：
  https://chen10eason-png.github.io/cpbl-atlas/data/manifest.json
  https://chen10eason-png.github.io/cpbl-atlas/data/2025.json
  https://chen10eason-png.github.io/cpbl-atlas/data/2026.json
  這三個地址都有正確 JSON，且選單有兩年，才算真實上線。

重要限制：
- 此工作流程負責真正執行現有官方抓取程式，不保證現有抓取器已能成功解析官網。
- 目前助手所連結的 GitHub 身分對 chen10eason-png/cpbl-atlas 只有讀取權限，無法代替你直接提交。
- 若 Actions 顯示匯入失敗，代表現在必須依據實際日誌修正爬蟲；不可以提供模擬 2025/2026 數據。
- 成功後排程會每天 08:15（台北時間）執行一次，GitHub 排程可能延遲。
- GitHub Actions 以 GITHUB_TOKEN 自行 commit 資料，不一定會觸發傳統 Pages build；本 workflow 同次直接部署 Pages。
