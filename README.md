# Hevy トレーニングログ (サンプル / テンプレート)

[Hevy](https://www.hevyapp.com/) のトレーニング記録を **テキストでエクスポートして貼るだけ** で、自分のGitHubリポジトリに無期限で保存し、BIG3(スクワット・ベンチプレス・デッドリフト)の進捗と成長グラフを自動で作るテンプレートです。

- Hevy は日々の記録を **見る場所**、GitHub は全期間の **保管庫**
- Hevy の有料プラン(API)は不要。無料版だと古い記録が見られなくなっても、ここには残る
- スマホだけで完結 (GitHubアプリで貼り付け → 自動で集計)
- 記録は `sets.csv` (1セット1行) なので、表計算ソフトやAIにもそのまま読ませられる

> **このリポジトリの `raw/` と `sets.csv` の中身はすべてダミー (架空の記録) です。** 動作を確認するためのサンプルで、「[自分用に使い始める](#自分用に使い始める)」の手順で消してから使います。

## できあがるもの

<!-- BIG3:START -->
### BIG3 進捗

| 種目 | 最大重量 | 日付 | 推定1RM(最高) | 目標 | 目標まで |
|---|---|---|---|---|---|
| スクワット (バーベル) | 87.5 kg | 2026-10-19 | 102.1 kg | 100 kg | +12.5 kg |
| ベンチプレス (バーベル) | 62.5 kg | 2026-10-21 | 72.9 kg | 70 kg | +7.5 kg |
| デッドリフト (バーベル) | 107.5 kg | 2026-10-23 | 125.4 kg | 120 kg | +12.5 kg |
| **合計** | **257.5 kg** | | **300.4 kg** | **290 kg** | **+32.5 kg** |

更新: 2026-10-27 00:05 / 推定1RMは Epley式 (回数12以下のセットのみ)
<!-- BIG3:END -->

目標は例として スクワット100kg / ベンチプレス70kg / デッドリフト120kg (合計290kg) にしてあります。

### 最大重量の推移 (実際に挙げた重量)
![BIG3の最大重量の推移](viz/big3_weight.svg)

### 推定1RMの推移 (Epley式・12回以下)
![BIG3の推定1RMの推移](viz/big3_1rm.svg)

点は各日の最重量セット(補助ありを除く)、実線はそれまでの自己ベスト、点線は目標です。ライト/ダークモードに自動で合わせます。

## 必要なもの
- Hevy アプリ (**日本語表示**。[注意](#注意と制限)を参照)
- GitHub アカウント
- PCで使う場合: Python 3.9 以上 と git (標準ライブラリだけで動くので `pip install` は不要)
- スマホだけで使う場合: GitHub アプリ (PCは初回の設定以外いりません)

## 自分用に使い始める

### 1. リポジトリを作る
1. このページ右上の **Use this template → Create a new repository**
2. **Private (非公開) を選ぶ**。`raw/` と `sets.csv` にはトレーニングの日時やワークアウトのURLが入ります
3. 名前は自由 (例: `hevy-log`) で作成

### 2. GitHub Actions に書き込み権限を与える (スマホから使う場合は必須)
自分のリポジトリで **Settings → Actions → General → Workflow permissions** を開き、**Read and write permissions** にして Save。

### 3. ダミーデータを消す
PCで clone して、リポジトリの中で:
```bash
git clone https://github.com/<あなたのユーザー名>/<リポジトリ名>.git
cd <リポジトリ名>
rm -f raw/*.txt sets.csv viz/*.svg
git add -A && git commit -m "サンプルデータを削除" && git push
```
- 最初に自分の記録を取り込むまで、README のグラフ画像は表示されません (取り込むと自動で作られます)
- 取り込み前の状態で `python3 hevy_import.py report` を実行しても、エラーにはならず0kgの表が出ます

### 4. 目標と種目名を自分用にする
`hevy_import.py` の先頭にある `BIG3` を編集します。
```python
BIG3 = {
    "スクワット (バーベル)": 100,      # ← 種目名: 目標の重量(kg)
    "ベンチプレス (バーベル)": 70,
    "デッドリフト (バーベル)": 120,
}
```
- **種目名は Hevy に表示される名前と完全に一致させる**必要があります (カッコの全角/半角、スペースも同じに)。違うと集計に入りません
- 種目は **3つ** です (グラフが3種目の前提です)。「バックスクワット」など別の種目を使っている場合は、名前だけ置き換えてください
- 年末目標のREADME表示や合計は、この数字から自動で作られます

### 5. 最初の記録を取り込む
下の「[毎日の使い方](#毎日の使い方)」の手順で、Hevy の記録を1回取り込みます。BIG3の3種目すべてに記録が入ると、表とグラフが作られます。

## 毎日の使い方

### Hevy からテキストをコピーする
ワークアウトの詳細画面の共有メニューから、記録を**テキストとして共有・コピー**します (アプリのバージョンによって表示名は違います)。次のような形式のテキストが取れていれば正解です。
```
Push
月曜日, 10月 26, 2026 6:56午前

ベンチプレス (バーベル)
"メモ (任意)"
セット 1: 65 kg x 8
セット 2: 65 kg x 7

@hevyapp
https://hevy.com/workout/xxxxxxxx
```
最後の `@hevyapp` と URL の行が **セッションの区切りと重複防止の目印** になるので、消さずに貼ってください。複数の記録をまとめて貼ることもできます。

### パターンA: スマホから (GitHubアプリ)
1. Hevy の記録テキストをコピー
2. GitHub アプリで自分のリポジトリを開く → `inbox` フォルダ → **Add file → Create new file**
3. ファイル名を `2026-10-27.txt` のように `.txt` で付けて、中身にテキストを貼り付け → Commit
4. 数十秒後に GitHub Actions が自動で取り込み、`sets.csv`・`raw/`・README の表とグラフを更新します (`inbox` のファイルは取り込み後に消えます)

### パターンB: PC から
```bash
git pull                       # スマホ経由の更新を先に取り込む
python3 hevy_import.py         # クリップボードのテキストを取り込む (macOS)
git add -A && git commit -m "import" && git push
```
- ファイルから取り込む: `python3 hevy_import.py --file export.txt`
- 同じセッションを2回取り込んでも、重複しません (HevyのURL末尾のIDで判定)
- 集計だけやり直す: `python3 hevy_import.py report`
- メモに特定の語を含む種目を集計から外す: `python3 hevy_import.py report --exclude-notes ポーズ,ラーセン`

### 内訳を見られるグラフ (PC)
```bash
python3 viz/build_growth.py && open viz/growth.html
```
ホバー/タップで日ごとの内訳が出て、推定1RMに使う回数の上限 (5/8/12回以下) を切り替えられます。このファイルはGit管理外で、ブラウザで開くだけです。

## 仕組み
```
Hevyのテキスト → inbox/*.txt → (Actions) hevy_import.py → sets.csv + raw/ + README表 + viz/*.svg
```
| ファイル | 内容 |
|---|---|
| `hevy_import.py` | テキストを分解して `sets.csv` に追記し、BIG3を集計して README とグラフを更新 |
| `sets.csv` | 1セット1行: `session_id, date, routine, exercise, exercise_note, set_no, weight_kg, reps` |
| `raw/` | セッションごとの元テキスト (やり直し用) |
| `inbox/` | スマホからの投入口 |
| `viz/` | グラフの生成スクリプト (`build_svg.py` = README用SVG、`build_growth.py` = ホバー付きHTML) |
| `.github/workflows/import.yml` | `inbox/*.txt` が追加されたら自動で取り込む |

- 推定1RM = 重量 × (1 + 回数 ÷ 30) (Epley式。1回はそのまま。13回以上のセットは除外)
- 単位が lbs の記録は kg に換算して保存します。自重種目 (`8 レップ数`) は重量が空欄になります
- 取り込めない行は捨てずに警告として表示されます

## 注意と制限
- **日本語表示の Hevy 専用です。** 日付の `月曜日, 10月 26, 2026 6:56午前` や `セット 1:` という日本語の書式を前提にしています。英語表示のエクスポートは形式が違うため、このままでは取り込めません (英語版のサンプルテキストがあれば対応を追加できます)
- BIG3 以外の種目も `sets.csv` には全部保存されますが、グラフと集計はBIG3 (3種目) だけです
- **非公開リポジトリで使ってください。** 公開する場合は `raw/` と `sets.csv` の日時・URLを削除またはマスクしてください

## よくある質問
**Actions が失敗する / 取り込まれない** → Settings → Actions → General の Workflow permissions が *Read and write* になっているか確認。Actions タブでログも見られます。ファイル名が `.txt` で、`inbox/` の直下にあることも確認してください。

**間違えて取り込んだ** → `sets.csv` の該当行 (`session_id` で探せます) と `raw/` の該当ファイルを消して commit します。

**種目名が違って集計されない** → `sets.csv` の `exercise` 列で実際の名前を確認し、`hevy_import.py` の `BIG3` をそれに合わせます。

**グラフが更新されない** → BIG3の3種目すべてに1回以上の記録が必要です。Actions のログに「グラフの更新に失敗」と出ていないか確認してください。

<details>
<summary>おまけ: 旧アプリ「筋トレMEMO」の履歴をスクショから取り込む (macOS)</summary>

Hevy に乗り換える前の記録が「筋トレMEMO」にある場合の、macOS 内蔵のOCRを使った取り込みツールが `kintorememo/` にあります (画像は Mac の外に出ません)。

1. 筋トレMEMOで種目の履歴画面を開き、**前の画面と1〜2日分が重なるように**スクロールしながらスクショを撮る
2. `raw/kintorememo/squat/` などに置く (この中の画像はGit管理外)
3. 実行
```bash
swiftc -O kintorememo/ocr.swift -o kintorememo/ocr      # 初回のみ
kintorememo/ocr raw/kintorememo/squat/*.(png|PNG) | python3 kintorememo/km_parse.py "スクワット (バーベル)" km_squat.csv
python3 kintorememo/km_merge.py km_squat.csv && python3 hevy_import.py report
```
- 各日の `TOTAL` (重量×回数の合計) と読み取り結果を照合し、合わない日は `NG` として表示して取り込みません
- Hevy に同じ日・同じ種目の記録がある日はスキップします
</details>
