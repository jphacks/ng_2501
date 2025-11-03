# バックエンドデザイン

## Baseモデルについて

base_agent.pyではmanimコードを生成するAIエージェントの基底クラスであるBaseモデルを定義しています。このBaseモデルの関心の中心は、「実行可能なmanimコードを生成し、実行して動画を作成すること」です。
この単一責任の原則 (Single Responsibility Principle) と密結合 (Tight Coupling) の回避をして疎結合にすることを目指したコードリファクタリングを行いました。
以下からはBaseモデルを継承することでAIエージェントサービスを作成してください。
Baseモデルは以下の機能を提供します。

- manimレンダリング機能
- manimコードの生成と改善のためのAIインターフェース
- manimコード作成のためのlogging機能
- manimコード実行のエラーハンドリング機能

### サブクラスが実装すべき中核ロジック

Baseモデルは抽象クラスとして設計されており、以下のメソッドを実装する必要があります。
- `generate_video(self,video_id:str,content:str,enhance_prompt:str,maxloop:int=3)->str:`: ユーザーのプロンプトに基づいてmanimコードを生成するメソッド。これを実装してください。
入力
    video_id: ユーザーの動画ID
    content: ユーザーのプロンプト
    enhance_prompt: プロンプト強化のための追加情報
出力は
return:
            生成の成功または失敗を示す文字列を返す。
            "Success": 成功
            "bad_request": セキュリティチェックに失敗
            "error": そのほかのエラー
            "failed": その他の失敗
となります。

　
### エージェントのエントリーポイント

エージェントサービスのエントリーポイントは`main`メソッドです。このメソッドを呼び出すことによって動画生成プロセスが開始され最終的にAPIへのレスポンスが返却されます。
