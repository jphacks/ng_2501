## issue番号（- #〇）

## やったこと（動作の確認のため、ある場合は動画や画像を添付してください）

## とくに見て欲しいところ

## 不安なところ

## その他情報（別で取った議事録等、このプルリクに関連する情報があれば）

---
<details>
  <summary>ブランチ名について</summary>

以下のいずれかをブランチの先頭につけてブランチを命名してください

- `feature/` 機能改修
- `bugfix/` バグ修正
- `refactor/` リファクタリング
- `deps/` 依存パッケージなどのアップデート
- `chore/` 雑用、当てはまるラベルがないときに設定する

例: `feature/login-button`

</details>

<details>
  <summary>reviewer・mergeについて</summary>

for 作業者：
- レビュー担当者には、ジャンルに分けて以下の人を任命する：
	- フロントエンド(デザイン)：**みつを**　まこちゃーん
  - フロントエンド(ロジック)：**まこちゃーん**　めろ
  - バックエンド(AIエージェント/RAG)：**やづや**（精度)　めろ(速度）
  - バックエンド(API・DBなどその他)：**まこちゃーん** やづや
  - ロゴ/スライドその他：みつを まこちゃーん めろ
  - インフラ（CI/CD)：やづや
- レビューが承認(Approve)されたらmergeする
- レビューが非承認なら再度作業してpushし、コメントでコミット番号を明示しレビュー担当をメンションする

for レビュワー：
- レビュー担当はレビューをしたらDiscordにそれを通知する
- レビューは、わからないことへの共通認識をつけることを目的として、とにかく質問する。質問が無ければOK
- フロントエンドについては、実際に依頼された人が成果物を動作させて確認する

※ 作業の担当外の人は勉強になったことなどをコメントできるとBetterです!
</details>
<details>
  <summary>レビューのコメントについて</summary>

レビュー時はバッヂ（テキストでも可）を付けて、どのレベル感のコメントか明示します。

- ![badge](https://img.shields.io/badge/review-must-red.svg) `[must]` 必ず直すべき
- ![badge](https://img.shields.io/badge/review-imo-orange.svg) `[imo]` 自分の考えは〜
- ![badge](https://img.shields.io/badge/review-nits-green.svg) `[nit]`細かい指摘
- ![badge](https://img.shields.io/badge/review-ask-blue.svg) `[ask]` 質問/確認
- ![badge](https://img.shields.io/badge/review-fyi-yellow.svg) `[fyi]` ご参考まで

例

md
![badge](https://img.shields.io/badge/review-fyi-yellow.svg)

また、基本的に担当者がわからないことを質問することをレビューとします。フロントエンドについては、実際に成果物を触ってチェックするウォークスルーレビューを行います。
</details>
