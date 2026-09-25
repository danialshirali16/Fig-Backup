<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Ícone do Fig Backup">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <b>Português</b> · <a href="README.ru.md">Русский</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.zh-CN.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="Status de build do branch windows-build"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**Salve cópias nativas dos seus arquivos do Figma no seu computador.** O Fig Backup é um aplicativo de desktop gratuito para Macs com Apple Silicon e Windows 10/11. Ele salva arquivos do Figma Design como `.fig`, arquivos do FigJam como `.jam` e arquivos do Figma Slides como `.deck`.

<p align="center">
  <img src="../screenshots/cover.png" alt="Capa do Fig Backup — backups nativos do Figma, aplicativo de desktop gratuito para macOS e Windows" width="100%">
</p>

## Download

Obtenha a [**versão mais recente**](https://github.com/danialshirali16/Fig-Backup/releases/latest):

| Plataforma | Download |
| --- | --- |
| macOS (Apple Silicon) | [Clique aqui](https://github.com/danialshirali16/Fig-Backup/releases/latest)|
| Windows 10/11 (x64) | [Clique aqui](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip)|

Cada versão também inclui um arquivo `SHA256SUMS.txt` com as somas de verificação dos dois arquivos.

Na primeira execução, o Fig Backup baixa o Chromium (cerca de 150 MB) como navegador de backup. O app do macOS não é assinado; pode ser necessário clicar com o botão direito e escolher **Open**. Para ajuda com a instalação, consulte [Solução de problemas](../TROUBLESHOOTING.md).

## Como começar

1. Crie um Figma Personal Access Token com as permissões `folders:read` e `file_metadata:read` (tokens antigos com `projects:read` também funcionam).
2. Abra o Fig Backup, cole o token e entre no Figma na janela do navegador que o app abre.
3. Escolha um time. Use **Download all**, ou **Select** para escolher pastas e arquivos específicos.

O login no navegador é necessário antes do primeiro backup; você pode adiá-lo durante a configuração e o app pedirá novamente quando for preciso. Depois disso, os backups rodam em segundo plano.

## O que é salvo?

- Arquivos do Figma Design, FigJam e Slides são salvos em seus formatos nativos:<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Arquivos do Figma Design">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="Arquivos do FigJam">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Arquivos do Figma Slides">
- Faça o backup de um time inteiro com um clique, ou use **Select** para escolher pastas e arquivos específicos.
- Backups de pastas preservam a estrutura de times e pastas.
- O gerenciador de downloads mostra o progresso ao vivo e permite tentar novamente, parar ou cancelar itens da fila. Tipos de arquivo não suportados são pulados e não contam no percentual de progresso.

Backups de times e pastas vão para `Downloads/Fig Backup/<Team>/<Folder>/…`. Arquivos individuais vão direto para `Downloads`. Se já existir um nome de arquivo, o Fig Backup adiciona um número em vez de sobrescrevê-lo.

## Como funciona

A API REST do Figma não oferece exportação nativa de arquivos. O Fig Backup usa um navegador para automatizar a ação **Save local copy** do editor do Figma — o que chega ao seu disco é exatamente o arquivo que o editor do Figma gera. Como isso depende da interface web do Figma, uma mudança futura do Figma pode exigir uma atualização do app.

## Capturas de tela

| Assistente de configuração | Pastas e arquivos |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="Assistente de configuração — etapa de login no navegador"> | <img src="../screenshots/browse-light.png" alt="Navegando pelas pastas e arquivos de um time"> |
| **Gerenciador de downloads** | **Modo escuro** |
| <img src="../screenshots/download-manager.png" alt="Gerenciador de downloads com uma fila em andamento"> | <img src="../screenshots/dark-mode.png" alt="Visualização de navegação no modo escuro"> |

## Privacidade e segurança

Os backups ficam no seu computador. O Fig Backup se comunica com o Figma para acessar seus arquivos e não envia seus arquivos nem seu token a nenhum servidor do Fig Backup, e não coleta telemetria.

Seu token fica armazenado em `~/Library/Application Support/Fig Backup/token.json` com permissões `0600`. Ele não fica no keychain do sistema e não tem criptografia própria — não use uma conta de usuário compartilhada. Para execução via script, a variável de ambiente `FIGMA_PAT` pode substituí-lo. Veja [SECURITY.md](../../SECURITY.md) para mais detalhes. Use o app apenas com arquivos que você tem autorização para acessar.

## Ajuda e contribuição

Problemas para instalar, entrar ou baixar? Leia [Solução de problemas](../TROUBLESHOOTING.md). Relatos de bugs e contribuições são bem-vindos; veja [CONTRIBUTING.md](../../CONTRIBUTING.md).

O Fig Backup é um projeto independente e não tem vínculo com o Figma. Distribuído sob a [Licença MIT](../../LICENSE).

## Doar

Se o Fig Backup economiza o seu tempo, apoie o desenvolvimento com Bitcoin:

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="QR Code de doação em Bitcoin" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> Este arquivo é uma tradução. O [README em inglês](../../README.md) é a versão oficial.
