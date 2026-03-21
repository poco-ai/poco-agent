<div align="center">

![Poco Hero](assets/hero.png)

# Poco: あなたのポケットコワーカー

より安全で、美しく、使いやすい OpenClaw の代替ツール

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue)](https://www.docker.com/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Docs](https://img.shields.io/badge/poco-docs-blueviolet)](https://docs.poco-ai.com/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/poco-ai/poco-agent)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md)

</div>

## 主な機能

- **セキュアサンドボックス**
  すべてのタスクは隔離されたコンテナ内で実行されます。依存関係のインストール、ファイルの変更、コマンドの実行を自由に行えます — ホスト環境に影響を与えることはありません。
- **チャットボット以上の存在**
  - プランモード、会話キューイング、会話の終了などに対応
  - **プロジェクト管理**: タスクやコンテキストの整理・切り替えをより効率的に
  - **ファイルアップロード**: 多様なファイル形式を受け入れて処理
- **洗練された生産性の高いUI**
  - **アーティファクトビュー**: 多くの形式をレンダリング・プレビュー（HTML、PDF、Markdown、画像、動画、Xmind、Excalidraw、Drawioなど）
  - **プレイバックビュー**: コマンドI/O、ブラウザセッション、Skills/MCPツール呼び出しを再生
  - **ライト/ダークモード** 対応
- **エージェンティックな体験**
  - **ネイティブ Claude Code 体験** - スラッシュコマンド、プランモード、AskQuestion など
  - **MCP & Skills** - 簡単にインポートでき、無限に拡張可能
  - **ブラウザ** - 自律的なウェブリサーチのための組み込みブラウザ
  - **GitHub リポジトリ連携** によるコード検索・編集
  - **バックグラウンド実行 & スケジュールトリガー** — ブラウザを閉じた後もクラウド上でエージェントが動作し続けます
- **インタラクション**
  - **モバイル対応**: いつでもどこでもエージェントを操作
  - **IM連携**: DingTalk、Feishu、Telegramによる組み込みバックエンドメッセージング、プッシュ通知、イベントサブスクリプション
  - **セルフホスティング**: Docker ワンクリックデプロイで完全なランタイム環境を構築
  - **クラウドサブスクリプション**: 近日公開予定
  - **多言語** 対応
- **スマートメモリ**
  **mem0** を搭載: エージェントがあなたの好み、プロジェクトのコンテキスト、過去のやり取りを記憶し、よりパーソナライズされたサポートを提供します。
- その他にも多くの強力な機能があなたを待っています！

## クイックスタート

インタラクティブなセットアップスクリプトを実行して、設定の自動生成とサービスの起動を行います：

```bash
./scripts/quickstart.sh
```

起動完了後、`http://localhost:3000` にアクセスしてください。

デプロイの詳細なドキュメントやトラブルシューティングについては、[デプロイガイド](https://docs.poco-ai.com/en/deployment)をご参照ください。

## スター履歴

[![Star History Chart](https://api.star-history.com/svg?repos=poco-ai/poco-agent&type=date&legend=top-left)](https://www.star-history.com/#poco-ai/poco-agent&type=date&legend=top-left)
