# CPBL ATLAS V0.3.0 — 中華職棒歷史數據與進階分析

**版本：2026-10-18。這是獨立的非官方研究網站。** 不屬於中華職棒大聯盟或野球革命，來源分開署名。

## V0.3 新增內容

1. **守備數據頁**：年度球員守備紀錄、守位、TC／PO／A／E／DP／TP／PB／CS／SB／FPCT，球隊／守位／最低守備機會篩選，表格排序、搜尋、分頁、CSV 輸出。舊資料來源支援 1990–2024；2025–2026 個人守備紀錄仍待來源接入，空白明確提示。
2. **聯盟分析頁**：依每隊打者及投手累積數據重新計算球隊 AVG／OBP／SLG／OPS、全壘打、得分、三振、盜壘、ERA／WHIP／K/9，提供橫向球隊比較。該頁標示「由球員紀錄彙整」，非官方獨立球隊統計，口徑不同時可能有差異。
3. **中職資訊頁**：正式來源入口（賽程、比賽看板、單項榜、全記錄、歷年 HR、球隊戰績、2026 進階數據、點將錄等）；尚未匯入的功能**只提供官方跳轉**，不假裝已有自身的賽程、即時比分或逐球紀錄。
4. **擴增打者**：HR%、TB/PA、PA/HR、BB−K%、官方原始 `OPS+`、官方原始 `BIP%`；延續 AVG、OBP、SLG、OPS、ISO、BABIP、K%、BB%、RC、GPA、SecA 等。
5. **擴增投手**：HR/BF%、IP/G，及官方原始 `ERA+`、`FIP`；延續 WHIP、K/9、BB/9、H/9、HR/9、K/BB、K-BB%、投球效率與條件式 FIP。
6. **官方 2025／2026 匯入器增強**：只在原始欄位存在時保存官方標準化指標；基本棒球帳務校驗（AB≥H≥2B+3B+HR、PA≥AB、ER≤R）、403 或資料缺頁不公布、不覆蓋既有正確快照；並加入限速、429/5xx 重試。
7. **球隊主客場**：如果官方上下半季表包含主客場分項，僅當勝敗和加總一致才保留與呈現。半季資料沿用 W/L/T 全年核對機制。
8. **生涯年份**：生涯載入改用 manifest 中實際已驗證的年份，因此正式同步後可包含 2025、2026，不再硬限到 2024。

## 資料覆蓋：不可混淆「程式支援」與「數據已匯入」

| 年度 | 來源 | 目前在 ZIP 的狀態 | GitHub Actions 執行後 |
|---|---|---|---|
| 1990–2024 | [ldkrsi/cpbl-opendata](https://github.com/ldkrsi/cpbl-opendata)，MIT | 具有 CSV 匯入器與遠端讀取功能；本 ZIP **不包含 35 年下載數據快照** | 正式首次同步成功，生成 `data/YYYY.json` |
| 2025 | [CPBL 全記錄查詢](https://www.cpbl.com.tw/stats/recordall?year=2025&kindcode=A&position=01) | **尚未取得完整可驗證快照**，官網可查數值，程式已接線 | 成功下載完整打投、核實各隊戰績與上下半季，才會列入本站年份 |
| 2026 | [CPBL 全記錄查詢](https://www.cpbl.com.tw/stats/recordall?year=2026&kindcode=A&position=01) | **尚未取得完整可驗證快照**，同上 | 完整核對成功才列入選單；每日同步檢查來源 |
| 2026 進階球路/擊球 | [stats.cpbl.com.tw](https://stats.cpbl.com.tw/rankings) | 僅有正確官方入口，**Trackman/PR 尚未匯入** | 本版排程尚不會自動取得該資料，需另外研究合法資料取得方式 |
| 2025–2026 守備／逐場／逐球 | CPBL / 其他授權來源 | 尚未匯入 | 預留後續獨立連接器，不能由打投年度數據推斷 |

**沒有聲稱已完成 2025、2026 全量抓取或網站已部署。** 由於本執行環境無法連線 CPBL 網站執行程式，2025/26 完整匯入須在 GitHub Actions 或其他可連線環境正式運行並觀察 log。若出現 403、網站改版、資料缺頁，必須先診斷，不能靠猜數字補洞。

## 安裝、第一次同步與網站部署

1. 在 GitHub 建立一個全新的 Public repository，例如 `cpbl-atlas`，用 `main` 當預設分支。
2. 將 ZIP **所有檔案以及隱藏資料夾 `.github/`** 上傳到 Repo 根目錄。
3. 設定 `Settings → Pages → Build and deployment → Source → GitHub Actions`。
4. 開啟 `Actions → Build and update CPBL Atlas → Run workflow`。第一次執行抓取 1990–2024 歷年資料，接著嘗試官方 2025／2026 匯入；可能耗費數分鐘到較長時間。
5. 到 Actions log 查看 `PASS 2025: ...` 及 `PASS 2026: ...`。若無，表示該年**尚未成功匯入**，不能當成正常。下載/保存 `data/manifest.json` 可檢查已成功公開的年份與 `generatedAt`。
6. 設定完成後，GitHub Actions 預定每日台灣時間早上約 08:15 檢查（GitHub 排程可能延遲）；失敗時**保留成功快照**，在 workflow summary 明確回報錯誤。

### 本機單元測試

```bash
pip install -r requirements-sync.txt
python -m unittest discover -s tests -v
npm test
python scripts/sync.py --full
python scripts/sync_halves.py --all
python scripts/sync_official.py --year 2025
python scripts/sync_official.py --year 2026
python -m http.server 8000
```

`npm test` 不需安裝 Node packages。歷年 `sync.py` 在來源失敗時會停止提交錯誤球季；`sync_official.py` 只接收經來源校核的全年球季。**以上同步指令需要網路與尊重來源服務條款**，不能因本地環境阻擋就視為網站已更新。

## 指標口徑與資格

- 比率榜（AVG/OPS/ERA/WHIP/OPS+ 等）預設達當年球隊已出賽場數 × 3.1 PA，投手相關榜依球隊已賽場數等量局數設定；累積數據榜不強加規定打席/局數。這是本網站的資格控制，**不取代 CPBL 官方獎項的特殊資格判決**。
- 官方 `OPS+`、`ERA+` 保持其原數值，沒有從年度打席數自行臆造場地校正模型。若同季跨隊的原始官方相對指標不具可合併性，合計列**清空而不是相加**。
- `FIP`：如果原始必要值完整，依全聯盟年度防禦率定常數計算；否則可顯示官方原始 FIP（僅有數值時）；缺值是 `—` 不是 `0`。
- 守備 FPCT＝(PO＋A)/TC；TC=0 則缺值。守備最低 TC 是自選分析門檻，並非官方守備金手套的資格認定。
- 投手 IP `5.1` 表示五局又一個出局數，不是 5.1 局。
- **WAR、wRC+、WPA、RE24、UZR、Framing、Trackman、擊球初速、仰角、Barrel 等仍未自行計算或正式匯入**，需要事件級資料、正確模型及相關授權；可先透過中職資訊頁進入官方進階平台。

## V0.4 之後仍需開發

- 2025–2026 守備、二軍、季後賽、總冠軍賽個人統計的完整官方授權來源與獨立驗證。
- 逐場賽程/比分/Box Score/先發/逐局結果（需研究並驗證 CPBL 公開賽程連接器）；獎項、年度個人獎、全壘打明細、球員異動的歷史資料匯入。
- 合法且可存檔的 2026 進階數據源、球員身份年際對照、詳細球員檔案、逐年趨勢與歷史紀錄搜尋。
- 更完整的公版資料庫/伺服器更新與來源稽核（現階段以小型單站 GitHub Actions + JSON 靜態快照為主）。

## 授權／附註

- `ldkrsi/cpbl-opendata` MIT 授權；要保留作者及授權聲明。
- `rebas-tw/rebas.tw-open-data` ODC-By 1.0；本版僅連結說明，沒有複製逐球原始資料。
- CPBL 官網公開資料不等於無限制重製授權。應尊重官網政策、擷取頻率、引用及資料再利用的合法性；日後若需大規模長期重製，應洽 CPBL 授權。
- 所有未驗證的匯入狀態以清楚文字呈現，不能使用模擬數字冒充官方數據。
