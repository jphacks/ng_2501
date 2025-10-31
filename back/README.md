

# 実行スクリプト

FastAPIを実行する場合には以下のコマンドを打ちます。
--reloadコマンドについては、今回のAIエージェントの性質上ファイル構造に対して変更が入ってしまうので必要はないです。

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 
```
