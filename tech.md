# プロジェクトで利用している主な技術

## Backend（`back/`）

### API・アプリケーション層
- FastAPI をアプリケーションフレームワークとして採用し、`back/app/main.py` でルーター登録・CORS 制御・ルートハンドラを定義。ローカル実行は `uvicorn` を利用。
- `back/app/router/animation.py` では `APIRouter` と Pydantic モデルを使って動画生成/取得 API を実装し、環境変数読み込みに `python-dotenv` を使用。

### LLM エージェント
- `back/app/service/agent.py`・`back/app/service/rag_agent.py` で LangChain の `PromptTemplate` や `RunnableSequence` を活用し、Google Gemini (`langchain_google_genai`) の各モデルを組み合わせて解説生成・スクリプト生成・自動修正フローを構築。
- `back/app/service/react_agent.py` では LangGraph を使った ReAct ループ制御により、Lint・実行結果・RAG 参照を織り交ぜた反復的なコード改善を実装。

### RAG / ベクトル検索
- Manim 公式ドキュメントを基に `back/app/tools/embeding_data/manim_chroma_db/` に永続化した Chroma ベクトルストアを構築し、`langchain_chroma` と `langchain_huggingface` を介して検索。
- 埋め込み生成には Hugging Face の `jinaai/jina-code-embeddings-1.5b`（`sentence-transformers`）を用い、`build_vector_db.py` などのスクリプトで事前計算。

### アニメーション生成とセキュリティ
- `back/app/service/agent.py` 内で生成した Manim スクリプトを一時ファイルに保存し、`subprocess` 経由で Manim CLI を実行して `back/media/videos/` 以下へ書き出し。
- 実行前に `back/app/tools/secure.py` の AST ベースガードで危険 API の混入を検査し、`back/app/tools/manim_lint.py` でエラートレースを解析して LLM にフィードバック。

### 品質管理
- `back/app/tools/lint.py` にて Ruff フォーマッタと Pyright 型チェックを連続実行するユーティリティを提供し、生成スクリプトの静的品質を担保。

### 環境と構成
- 依存管理は `back/pyproject.toml` と `back/uv.lock` で行い、Python 3.11 を前提。
- `.env` に定義した API キー類を `dotenv` でロードし、`back/tmp/` ディレクトリで生成スクリプトを管理。

## Frontend（`front/`）

### フレームワークとビルド
- Next.js 15（App Router）と React 19・TypeScript 5 を採用し、`next dev --turbopack` で開発ビルド、`next build` で本番ビルドを実行。
- `tailwindcss`・`postcss`・`autoprefixer` を組み合わせ、`src/app/globals.css` から Tailwind のレイヤーとカスタムアニメーションを適用。
- プロジェクト全体の整形・静的解析は Biome (`pnpm lint` / `pnpm format`) で行い、`biome.json` に設定をまとめる。

### 数式入力とプレビュー
- `mathlive` を CDN Script + 動的 import で読み込み、`src/components/math/MathField.tsx`・`MathEditor.tsx` で仮想キーボードや LaTeX 補完を備えた数式入力 UI を構築。
- `src/app/hooks/useMathField.ts` と `useMathAutocomplete.ts` で MathLive の状態管理・Gemini 補完 API を連携し、`useTouchDevice.ts` でデバイス別の入力最適化を実装。
- Markdown プレビューは `react-markdown` + `remark-math` + `remark-gfm` + `rehype-katex` で実現し、KaTeX スタイルを `globals.css` から読み込む。

### LLM 連携と API コール
- フロントエンドからも Google Gemini API を使用し、`src/app/hooks/useGeminiAPI.ts` でタイトルからのノート生成・LaTeX 補完を実装（環境変数 `NEXT_PUBLIC_GEMINI_API_KEY`・`NEXT_PUBLIC_GEMINI_MODEL` を使用）。
- バックエンド連携は `src/app/hooks/useTextAnalysis.ts` のカスタムフックで実装し、`fetchVideo.ts` で生成済み動画を `URL.createObjectURL` 経由で取得。
- `VideoGenerationFlow` コンポーネントが `Landing`→`Generating`→`Result` の状態遷移を管理し、再生成時は編集プロンプトを前回リクエストとマージ。

### UI コンポーネント
- `Landing` 画面で Markdown + LaTeX の入力、プロンプト生成、動画追加指示を提供し、Gemini によるサンプル生成機能を搭載。
- `Result` 画面で動画プレイヤー（スクロール時のミニプレイヤー含む）と再生成フォーム、生成時プロンプト確認 UI を提供。
- エラーハンドリングは `ErrorContext` コンテキストで集約し、数式関連エラーは `MathError` 系ユーティリティでロギング。

### 環境変数と構成
- `.env.local` 等で `NEXT_PUBLIC_API_URL`（バックエンド URL）と Gemini 関連キーを設定し、`resolveBackendUrl()` でクライアント側の API エンドポイントを生成。
- Tailwind・Next.js・TypeScript の設定はそれぞれ `tailwind.config.ts`・`next.config.js`・`tsconfig.json` に集約し、`pnpm-lock.yaml` で依存を固定。
