# tips-maker

## ユーザーの課題

- スマホで数式を書くのは難しい
- 数式をわかりやすく伝えたい
- 教師がわかりやすい動画教材を作りたい

## 解決法

- スマホからでも入力できるライティング機能
- 数式を動画化してわかりやすく伝える
- manimを使った高品質な数学動画の自動生成

## 主な機能

### 1. テキスト入力機能（ランディングページ）

数式を含むテキストをWebフォームから入力し、動画生成のためのプロンプトを自動生成する。

**入力**

- **必須**: 数式を含むテキスト（めろくんなどが作成）
  - LaTeX形式の数式に対応（例: `\int_0^1 x^2 dx`）
  - 通常のテキストと数式を混在可能
  - 具体例: 「積分の基本的な計算方法を説明します。\int_0^1 x^2 dx = [x^3/3]_0^1 = 1/3」
- **任意**: 動画生成のプロンプト（トグルで表示/非表示）
  - 動画の見た目や演出の指示
  - 具体例: 「積分記号を赤色で強調してほしい」「計算過程をゆっくり表示してほしい」

**出力**

- `VideoGenerationPrompt`オブジェクト
  - `prompt`: AIが生成した動画生成用プロンプト（テキスト形式）
  - `manimCode`: manimで動画を生成するためのPythonコード
  - `originalText`: ユーザーが入力した元のテキスト

### 2. 中間プロンプト確認・編集機能

AIが自動生成したプロンプトとmanimコードを確認・編集する。AIの誤認識やタイポを修正可能。

**表示・編集内容**

- **編集可能なプロンプト**
  - AIが生成した動画生成プロンプトを自由に編集
- **原文表示**（トグル）
  - ユーザーが最初に入力したテキストを表示
  - AIがどのように解釈したか確認できる
- **Manimコード編集**（トグル）
  - AIが生成したPythonコード（manim）を表示・編集

**操作**

- 「動画を生成」ボタンで次のステップへ進む
- 編集内容は動画生成時に反映される

### 3. 動画生成機能

編集済みのプロンプトとmanimコードを使用して、数式解説動画を自動生成する。

**入力**

- `VideoGenerationPrompt`オブジェクト
  - ユーザーが確認・編集済みのプロンプト
  - manimコード

**処理**

- manimを使用した動画レンダリング
- LaTeX形式の数式を高品質な動画に変換
- 数式の変形過程をアニメーション化

**出力**

- `VideoResult`オブジェクト
  - `videoUrl`: 生成された動画ファイルのURL（MP4形式）
  - `prompt`: 使用されたプロンプト情報

### 4. 動画編集・再生成機能

生成された動画に対して追加の指示を出し、動画を再生成できます。

**表示内容**

- 生成された動画（videoタグで再生可能）
- 使用されたプロンプトの確認
- 動画の生成日時

**編集機能**

- **編集ダイアログ**
  - 「動画を編集する」ボタンで表示
  - 修正指示をテキストで入力
  - 具体例: 「図と式が重なっているので、図を左にずらしてください」「文字サイズを大きくしてください」
- **再生成**
  - 編集指示を元に動画を再生成
  - 既存のプロンプトに追加の指示を適用

**入力**

- `VideoEditRequest`オブジェクト
  - `videoId`: 編集対象の動画ID（videoUrl）
  - `editPrompt`: 修正内容の指示（テキスト）

**出力**

- 新しい`VideoResult`オブジェクト（再生成された動画）

### 5. 共有機能（今後実装予定）

ユーザー同士で作成した動画を共有できる。数学の単元ごとに整理されたブログ的な機能。

## 技術構成

### フロントエンド

- **ランタイム管理**: fnm (Fast Node Manager)
- **パッケージマネージャー**: pnpm
- **フレームワーク**: Next.js 15.5.4 + React 19.1.0
- **ビルドツール**: Turbopack
- **リンター・フォーマッター**: Biome
- **スタイリング**: Tailwind CSS
- **型安全性**: TypeScript

#### 数式関連ライブラリ
- **MathLive 0.107.1**: インタラクティブな数式エディタ（仮想キーボード対応）
- **KaTeX 0.16.23**: 高速な LaTeX 数式レンダリング
- **rehype-katex 7.0.1**: Markdown 内の LaTeX 数式処理
- **remark-math 6.0.0**: Markdown での数式記法サポート

#### Markdown関連
- **react-markdown 10.1.0**: React用Markdownレンダラー
- **remark-gfm 4.0.1**: GitHub Flavored Markdown サポート

### バックエンド

- **動画生成**: manim (Mathematical Animation Engine)
- **LaTeX処理**: TinyTeX + required packages
- **AI処理**: LLM（Gemini API / WebLLM等を検討中）
- **データベース**: SQLite（将来的に）

### インフラ

- **コンテナ化**: Docker
- **開発環境**: devcontainer対応

## 環境構築

### 前提条件

- Node.js 18以上（fnm推奨）
- pnpm

#### fnmのインストール

Node.jsのバージョン管理にfnmを使用します。

**macOS/Linux:**

```bash
curl -fsSL https://fnm.vercel.app/install | bash
```

**インストール後、Node.jsをインストール:**

```bash
fnm install 20
fnm use 20
```

#### pnpmのインストール

pnpmがインストールされていない場合は、以下のコマンドでインストール

```bash
npm install -g pnpm
```

### セットアップ手順

1. **依存関係のインストール**

   ```bash
   pnpm install
   ```

2. **開発サーバーの起動（Turbopack使用）**

   ```bash
   pnpm dev
   ```

   ブラウザで <http://localhost:3000> にアクセス

3. **コードのリンティング・フォーマット**

   ```bash
   # リンティングチェック
   pnpm lint
   
   # リンティングと自動修正
   pnpm lint:fix
   
   # コードフォーマット
   pnpm format
   ```

### プロジェクト構造

```text
tips-maker/
├── src/
│   ├── app/
│   │   ├── datas/                    # Domain層: データモデル定義・バリデーション
│   │   │   ├── Video.ts              # 動画生成のメインモデル（リクエスト、プロンプト、結果）
│   │   │   ├── Persona.ts            # ペルソナモデル（旧要件からの移行用）
│   │   │   ├── Tips.ts               # TIPSモデル（旧要件からの移行用）
│   │   │   ├── MathError.ts          # エラーハンドリング定義
│   │   │   ├── MathExpression.ts     # 数式表現のモデルと操作
│   │   │   ├── MathValidation.ts     # LaTeX バリデーション
│   │   │   └── GeminiConfig.ts       # Gemini API 設定
│   │   ├── hooks/                    # UseCase層: ビジネスロジック・API処理
│   │   │   ├── useTextAnalysis.ts    # 動画生成フロー全体のロジック
│   │   │   ├── useMathField.ts       # 数式フィールドの状態管理
│   │   │   ├── useMathAutocomplete.ts # 数式オートコンプリート
│   │   │   ├── useTouchDevice.ts     # タッチデバイス検出
│   │   │   └── useGeminiAPI.ts       # Gemini API 呼び出し
│   │   ├── contexts/                 # Contextプロバイダー
│   │   │   └── ErrorContext.tsx      # エラー通知管理
│   │   ├── layout.tsx                # ルートレイアウト
│   │   ├── page.tsx                  # トップページ
│   │   └── globals.css               # グローバルスタイル
│   ├── components/                   # Presentation層: UIコンポーネント
│   │   ├── VideoGenerationFlow.tsx   # 状態管理
│   │   ├── landing/                  # 状態1: ランディングページ
│   │   │   ├── Landing.tsx           # ランディングページ全体のラッパー
│   │   │   └── MathTextInput.tsx     # 数式テキスト入力フォーム
│   │   ├── prompt/                   # 状態2: プロンプト確認ページ
│   │   │   ├── Prompt.tsx            # プロンプト確認ページ全体のラッパー
│   │   │   └── PromptEditor.tsx      # プロンプト・Manimコード編集UI
│   │   ├── generating/               # 状態3: 動画生成中
│   │   │   └── Generating.tsx        # ローディング表示
│   │   ├── result/                   # 状態4: リザルトページ
│   │   │   ├── Result.tsx            # リザルトページ全体
│   │   │   ├── VideoPlayer.tsx       # 動画プレイヤー
│   │   │   └── VideoEditDialog.tsx   # 動画編集ダイアログ
│   │   └── math/                     # 数式編集コンポーネント
│   │       ├── MathField.tsx         # MathLive ラッパー
│   │       ├── LazyMathField.tsx     # 遅延ロード対応
│   │       └── MathEditor.tsx        # 数式エディタ（オートコンプリート付き）
│   ├── utils/                        # ユーティリティ関数
│   │   ├── mathLiveUtils.ts          # MathLive 初期化・操作
│   │   └── touchUtils.ts             # タッチデバイス最適化
│   └── styles/                       # 追加スタイル
│       └── math-editor.css           # 数式エディタ専用CSS
├── biome.json                        # Biome設定ファイル
└── package.json                      # 依存関係とスクリプト
```

#### アーキテクチャ

1. **Domain層** (`src/app/datas/`)
   - **役割**: ビジネスドメインのデータモデル定義とバリデーション
   - **主要ファイル**:
     - `Video.ts`: 動画生成リクエスト、プロンプト、結果の型定義
     - `Persona.ts`: ペルソナ（学習者プロファイル）モデル
     - `Tips.ts`: TIPS（学習コンテンツ）モデル
     - `MathError.ts`: エラークラスとエラーハンドリング
     - `MathExpression.ts`: 数式データ型、Markdown内の数式操作
     - `MathValidation.ts`: LaTeX式のバリデーションロジック
     - `GeminiConfig.ts`: Gemini API設定とデータ型

2. **UseCase層** (`src/app/hooks/`)
   - **役割**: ビジネスロジック、API通信、状態管理
   - **主要ファイル**:
     - `useTextAnalysis.ts`: 動画生成フローのコアロジック
     - `useMathField.ts`: 数式入力フィールドの状態管理
     - `useMathAutocomplete.ts`: Gemini APIを使用した数式補完
     - `useTouchDevice.ts`: タッチデバイス検出とUI最適化
     - `useGeminiAPI.ts`: Gemini API呼び出しロジック

3. **Presentation層** (`src/components/`)
   - **役割**: UIコンポーネント、ユーザーインタラクション、状態に基づく画面表示
   - **主要ファイル**:
     - `VideoGenerationFlow.tsx`: **アプリ全体のフロー制御**
   - **状態別コンポーネント**:
     1. `landing/`: テキスト入力画面（数式入力対応）
     2. `prompt/`: プロンプト確認・編集画面
     3. `generating/`: 動画生成中のローディング画面
     4. `result/`: 動画表示・編集画面
     5. `math/`: 数式エディタコンポーネント（MathLive統合）

## UI/UX

- **デザイン**: PC優先だけどスマホ対応（レスポンシブデザイン）
- **ページ遷移**: 将来的にはページ遷移なしがいい
- **トグル**: 詳細設定やmanim原文は必要に応じて表示したいね

## 今後の実装予定

- [ ] 数式入力機能（LaTeX形式対応）
- [ ] プロンプト生成機能（AI統合）
- [ ] 中間プロンプト編集UI
- [ ] manim連携・動画生成機能
- [ ] 動画プレイヤー実装
- [ ] 動画編集・再生成機能
- [ ] 共有機能（ブログ的な機能）
- [ ] 単元ごとの分類機能
- [ ] データベース統合
