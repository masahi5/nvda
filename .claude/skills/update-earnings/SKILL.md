---
name: update-earnings
description: NVIDIA(NVDA)の直近四半期決算を調査して data/earnings.json を更新し、コミットしてリポジトリに push する。ユーザーが「決算を更新」「最新決算を取得」などと依頼したときに使う。
---

# NVIDIA 決算まとめの更新と push

`data/earnings.json` は**手動更新の静的データ**（pipelineの自動取得対象外）。このスキルは最新の四半期決算を調べて当ファイルを書き換え、commit / push まで行う。

データは GitHub Pages 配信かつ Service Worker で `/data/` は network-first のため、**`sw.js` のキャッシュ名を上げる必要はない**（本体HTML/JS/CSSを変えた時だけ必要）。

## 手順

### 1. 現在の内容と日付を確認
- `data/earnings.json` を読み、いま記載されている `quarter` / `report_date` を把握する。
- 今日の日付を確認する（環境のcurrentDate）。

### 2. 直近の決算を調査
- WebSearch で NVIDIA の最新四半期決算を調べる。**公式の一次情報**を優先する:
  - NVIDIA Newsroom: `https://nvidianews.nvidia.com/news/nvidia-announces-financial-results-for-...`
  - NVIDIA IR: `https://investor.nvidia.com/`
- NVIDIA の会計年度はズレている（FYは1月末締め）。発表時期の目安:
  - Q1（4月末締め）→ 5月下旬発表
  - Q2（7月末締め）→ 8月下旬発表
  - Q3（10月末締め）→ 11月下旬発表
  - Q4・通期（1月末締め）→ 2月下旬発表
- 既存ファイルの `quarter` と同じ四半期しか見つからない場合は、**まだ新しい決算が出ていない**。その旨をユーザーに伝え、更新せず終了する（無理に書き換えない）。
- WebFetch で公式プレスリリースを開き、数値を裏取りする。最低限そろえる項目:
  - 総売上高（前年比・前期比・過去最高か）
  - データセンター売上（前年比）
  - 非GAAP EPS（とGAAP EPS）
  - 粗利率（非GAAP / GAAP）
  - 次四半期の売上ガイダンス
  - 配当・自社株買い等のトピック（あれば）

### 3. data/earnings.json を更新
既存スキーマを厳守する（フィールドの増減はしない）。日本語で簡潔に書く。

```json
{
  "quarter": "FY2027 Q2",
  "period_end": "2026-07-27",
  "report_date": "2026-08-27",
  "summary": "1〜2文の概要（売上・牽引要因・ガイダンス等）",
  "highlights": [
    { "label": "売上高", "value": "$xx.xB", "note": "前年比 +xx% / 過去最高" },
    { "label": "データセンター売上", "value": "$xx.xB", "note": "前年比 +xx%" },
    { "label": "非GAAP EPS", "value": "$x.xx", "note": "GAAP $x.xx" },
    { "label": "Q3ガイダンス", "value": "約$xxB", "note": "売上見通し" }
  ],
  "sources": [
    { "label": "NVIDIA公式プレスリリース", "url": "https://nvidianews.nvidia.com/news/..." },
    { "label": "投資家向け (IR)", "url": "https://investor.nvidia.com/news/press-release-details/..." }
  ],
  "updated_at": "YYYY-MM-DD"
}
```

注意:
- `highlights` は4〜6項目程度。フロント（`renderEarnings`）が `label` / `value` / `note` をカード表示する。
- `sources` の URL は必ず実在を確認した一次情報にする（推測URLを置かない）。
- `updated_at` は今日の日付。
- 日付は `period_end` / `report_date` ともに ISO（YYYY-MM-DD）。

### 4. 妥当性チェック
- JSON としてパースできることを確認（例: `uv run --project pipeline python -c "import json;json.load(open('data/earnings.json',encoding='utf-8'));print('OK')"`）。

### 5. コミットして push
- 変更が `data/earnings.json` のみであることを `git status` で確認。
- Actions のデータ更新botが頻繁に push するため、**push前に必ず rebase** する:
  ```
  git add data/earnings.json
  git commit -m "data: 決算まとめを <quarter> に更新" -m "Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
  git pull --rebase origin main
  git push origin main
  ```
  ※ コミット前に未ステージのまま `git pull --rebase` するとエラーになるので、先に commit してから rebase する。
- push 成功後、反映確認方法を一言添える（`/data/` は network-first なので通常リロードで反映、SWキャッシュ更新は不要）。

## 完了報告
- どの四半期に更新したか、主要数値、情報元URL、push結果（コミットハッシュ）を簡潔に伝える。
- 新しい決算が未発表で更新しなかった場合は、その旨と次回発表の目安時期を伝える。
