<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Fig Backup のアイコン">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.pt-BR.md">Português</a> · <a href="README.ru.md">Русский</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.zh-CN.md">中文</a> · <b>日本語</b>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="windows-build ブランチのビルド状況"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**Figmaファイルのネイティブコピーを自分のコンピュータに保存しましょう。** Fig BackupはApple Silicon MacとWindows 10/11向けの無料デスクトップアプリです。Figma Designのファイルを`.fig`として、FigJamのファイルを`.jam`として、Figma Slidesのファイルを`.deck`として保存します。

<p align="center">
  <img src="../screenshots/cover.png" alt="Fig Backupのカバー — Figmaからのネイティブバックアップ、macOSとWindows向けの無料デスクトップアプリ" width="100%">
</p>

## ダウンロード

[**最新リリース**](https://github.com/danialshirali16/Fig-Backup/releases/latest)を入手：

| プラットフォーム | ダウンロード |
| --- | --- |
| macOS（Apple Silicon） | [こちらをクリック](https://github.com/danialshirali16/Fig-Backup/releases/latest)|
| Windows 10/11（x64） | [こちらをクリック](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip)|

各リリースには、両ファイルのチェックサムを記録した`SHA256SUMS.txt`も同梱されています。

初回起動時に、Fig Backupはバックアップ用ブラウザとしてChromium（約150 MB）をダウンロードします。macOS版アプリは未署名のため、右クリックして**Open**を選ぶ必要がある場合があります。インストールでお困りの際は[トラブルシューティング](../TROUBLESHOOTING.md)をご覧ください。

## はじめに

1. `folders:read`と`file_metadata:read`の権限を持つFigma Personal Access Tokenを作成します（`projects:read`付きの古いトークンも使えます）。
2. Fig Backupを開き、トークンを貼り付けて、アプリが開くブラウザウィンドウでFigmaにサインインします。
3. チームを選びます。**Download all**で一括取得するか、**Select**で特定のフォルダやファイルを選択します。

最初のバックアップの前にブラウザでのサインインが必要です。セットアップ中に後回りにすることもでき、必要になればアプリが再度案内します。設定後、バックアップはバックグラウンドで実行されます。

## バックアップの内容

- Figma Design、FigJam、Slidesのファイルはそれぞれのネイティブ形式で保存されます：<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Figma Designのファイル">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="FigJamのファイル">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Figma Slidesのファイル">
- ワンクリックでチーム全体をバックアップしたり、**Select**で特定のフォルダやファイルを選んだりできます。
- フォルダのバックアップではチームとフォルダの構造が保たれます。
- ダウンロードマネージャーが進行状況をライブ表示し、キュー内の項目の再試行・停止・キャンセルができます。未対応のファイル形式はスキップされ、進捗率には含まれません。

チームやフォルダのバックアップは`Downloads/Fig Backup/<Team>/<Folder>/…`に保存されます。単一ファイルは`Downloads`に直接保存されます。同名ファイルが既にある場合、Fig Backupは上書きせずに番号を付けます。

## 仕組み

FigmaのREST APIにはファイルのネイティブ書き出しがありません。Fig BackupはブラウザでFigmaエディタの**Save local copy**操作を自動化するため、ディスクに届くのはFigmaエディタが生成するのと同じファイルです。これはFigmaのWebインターフェースに依存するため、将来のFigmaの変更によってアプリの更新が必要になる可能性があります。

## スクリーンショット

| セットアップウィザード | フォルダとファイル |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="セットアップウィザード — ブラウザサインインのステップ"> | <img src="../screenshots/browse-light.png" alt="チームのフォルダとファイルを閲覧"> |
| **ダウンロードマネージャー** | **ダークモード** |
| <img src="../screenshots/download-manager.png" alt="実行中のキューがあるダウンロードマネージャー"> | <img src="../screenshots/dark-mode.png" alt="ダークモードのブラウズ画面"> |

## プライバシーとセキュリティ

バックアップはあなたのコンピュータに保存されます。Fig BackupはファイルへアクセスするためにFigmaと通信しますが、あなたのファイルやトークンをFig Backupのサーバーにアップロードすることはなく、テレメトリーも収集しません。

トークンは`~/Library/Application Support/Fig Backup/token.json`に権限`0600`で保存されます。システムのキーチェーンには保存されず、個別の暗号化もありません — 共有アカウントでは使わないでください。スクリプト実行時は環境変数`FIGMA_PAT`で上書きできます。詳細は[SECURITY.md](../../SECURITY.md)。アクセスが許可されたファイルにのみ使用してください。

## ヘルプとコントリビューション

インストール、サインイン、ダウンロードでお困りですか？[トラブルシューティング](../TROUBLESHOOTING.md)をお読みください。バグ報告やコントリビューションを歓迎します。[CONTRIBUTING.md](../../CONTRIBUTING.md)をご覧ください。

Fig Backupは独立したプロジェクトで、Figmaとは提携していません。[MITライセンス](../../LICENSE)で公開されています。

## 寄付

Fig Backupがお役に立ったら、Bitcoinで開発を支援できます：

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="Bitcoin寄付QRコード" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> このファイルは翻訳です。正式版は[英語のREADME](../../README.md)です。
