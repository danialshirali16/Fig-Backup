<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Fig Backup 图标">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.pt-BR.md">Português</a> · <a href="README.ru.md">Русский</a> · <a href="README.tr.md">Türkçe</a> · <b>中文</b> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="windows-build 分支的构建状态"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**将 Figma 文件的原生副本保存到你的电脑。** Fig Backup 是一款适用于 Apple Silicon Mac 和 Windows 10/11 的免费桌面应用。它将 Figma Design 文件保存为 `.fig`，FigJam 文件保存为 `.jam`，Figma Slides 文件保存为 `.deck`。

<p align="center">
  <img src="../screenshots/cover.png" alt="Fig Backup 封面 — 来自 Figma 的原生备份，适用于 macOS 和 Windows 的免费桌面应用" width="100%">
</p>

## 下载

获取[**最新版本**](https://github.com/danialshirali16/Fig-Backup/releases/latest)：

| 平台 | 下载 |
| --- | --- |
| macOS（Apple Silicon） | [点击此处](https://github.com/danialshirali16/Fig-Backup/releases/latest)|
| Windows 10/11（x64） | [点击此处](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip)|

每个版本还附带 `SHA256SUMS.txt`，包含这两个文件的校验和。

首次启动时，Fig Backup 会下载 Chromium（约 150 MB）作为备份浏览器。macOS 应用未经签名，你可能需要右键点击它并选择 **Open**。安装方面的问题请参阅[故障排除](../TROUBLESHOOTING.md)。

## 快速开始

1. 创建一个具有 `folders:read` 和 `file_metadata:read` 权限的 Figma Personal Access Token（带 `projects:read` 的旧令牌也可以使用）。
2. 打开 Fig Backup，粘贴令牌，并在应用打开的浏览器窗口中登录 Figma。
3. 选择一个团队。点击 **Download all**，或使用 **Select** 挑选特定的文件夹和文件。

首次备份前需要在浏览器中登录；你可以在设置时暂时跳过，需要时应用会再次提示。设置完成后，备份将在后台运行。

## 会备份什么？

- Figma Design、FigJam 和 Slides 文件以其原生格式保存：<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Figma Design 文件">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="FigJam 文件">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Figma Slides 文件">
- 一键备份整个团队，或使用 **Select** 选择特定的文件夹和文件。
- 文件夹备份会保留团队和文件夹结构。
- 下载管理器实时显示进度，可重试、停止或取消队列中的项目。不受支持的文件类型会被跳过，不计入进度百分比。

团队和文件夹备份保存到 `Downloads/Fig Backup/<Team>/<Folder>/…`。单个文件直接保存到 `Downloads`。如果文件名已存在，Fig Backup 会添加编号而不是覆盖。

## 工作原理

Figma 的 REST API 不提供原生文件导出。Fig Backup 通过浏览器自动执行 Figma 编辑器的 **Save local copy** 操作，因此保存到磁盘的正是 Figma 编辑器生成的同一个文件。由于这依赖 Figma 的网页界面，Figma 未来的改动可能需要更新应用。

## 截图

| 设置向导 | 文件夹与文件 |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="设置向导 — 浏览器登录步骤"> | <img src="../screenshots/browse-light.png" alt="浏览团队的文件夹和文件"> |
| **下载管理器** | **深色模式** |
| <img src="../screenshots/download-manager.png" alt="正在运行队列的下载管理器"> | <img src="../screenshots/dark-mode.png" alt="深色模式下的浏览视图"> |

## 隐私与安全

备份保存在你自己的电脑上。Fig Backup 会与 Figma 通信以访问你的文件，但绝不会将你的文件或令牌上传到任何 Fig Backup 服务器，也不收集遥测数据。

令牌存储在 `~/Library/Application Support/Fig Backup/token.json`，权限为 `0600`。它不保存在系统钥匙串中，也没有单独加密 — 请勿在共享用户账户上使用。脚本启动时可用环境变量 `FIGMA_PAT` 覆盖。详见 [SECURITY.md](../../SECURITY.md)。请仅对你有权访问的文件使用本应用。

## 帮助与贡献

安装、登录或下载遇到问题？请阅读[故障排除](../TROUBLESHOOTING.md)。欢迎提交错误报告和贡献代码，参见 [CONTRIBUTING.md](../../CONTRIBUTING.md)。

Fig Backup 是一个独立项目，与 Figma 无关联。基于 [MIT 许可证](../../LICENSE) 发布。

## 捐赠

如果 Fig Backup 为你节省了时间，欢迎用比特币支持它的开发：

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="比特币捐赠二维码" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> 本文件为翻译版本，以[英文 README](../../README.md) 为准。
