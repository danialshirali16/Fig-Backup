<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Fig Backup-Symbol">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <b>Deutsch</b> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.pt-BR.md">Português</a> · <a href="README.ru.md">Русский</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.zh-CN.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="Build-Status des windows-build-Zweigs"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**Sichern Sie native Kopien Ihrer Figma-Dateien auf Ihrem Rechner.** Fig Backup ist eine kostenlose Desktop-App für Apple-Silicon-Macs und Windows 10/11. Sie speichert Figma-Design-Dateien als `.fig`, FigJam-Dateien als `.jam` und Figma-Slides-Dateien als `.deck`.

<p align="center">
  <img src="../screenshots/cover.png" alt="Fig Backup Cover — native Backups aus Figma, kostenlose Desktop-App für macOS und Windows" width="100%">
</p>

## Download

Holen Sie sich die [**neueste Version**](https://github.com/danialshirali16/Fig-Backup/releases/latest):

| Plattform | Download |
| --- | --- |
| macOS (Apple Silicon) | [Hier klicken](https://github.com/danialshirali16/Fig-Backup/releases/latest)|
| Windows 10/11 (x64) | [Hier klicken](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip)|

Jede Version enthält außerdem eine `SHA256SUMS.txt` mit Prüfsummen für beide Dateien.

Beim ersten Start lädt Fig Backup Chromium (ca. 150 MB) als Backup-Browser herunter. Die macOS-App ist unsigniert; möglicherweise müssen Sie mit der rechten Maustaste klicken und **Open** wählen. Hilfe bei der Installation finden Sie in der [Fehlerbehebung](../TROUBLESHOOTING.md).

## Erste Schritte

1. Erstellen Sie einen Figma Personal Access Token mit den Berechtigungen `folders:read` und `file_metadata:read` (ältere Tokens mit `projects:read` funktionieren ebenfalls).
2. Öffnen Sie Fig Backup, fügen Sie den Token ein und melden Sie sich im Browserfenster der App bei Figma an.
3. Wählen Sie ein Team. Klicken Sie auf **Download all**, oder verwenden Sie **Select**, um bestimmte Ordner und Dateien auszuwählen.

Die Browser-Anmeldung ist vor dem ersten Backup erforderlich; Sie können sie während des Setups aufschieben, und die App fragt bei Bedarf erneut. Danach laufen Backups im Hintergrund.

## Was wird gesichert?

- Figma-Design-, FigJam- und Slides-Dateien werden in ihrem jeweiligen nativen Format gespeichert:<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Figma-Design-Dateien">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="FigJam-Dateien">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Figma-Slides-Dateien">
- Sichern Sie ein ganzes Team mit einem Klick, oder wählen Sie mit **Select** bestimmte Ordner und Dateien aus.
- Ordner-Backups behalten die Team- und Ordnerstruktur bei.
- Der Download-Manager zeigt den Fortschritt live an und ermöglicht es, Einträge in der Warteschlange erneut zu versuchen, zu stoppen oder abzubrechen. Nicht unterstützte Dateitypen werden übersprungen und zählen nicht zur Fortschrittsanzeige.

Team- und Ordner-Backups landen in `Downloads/Fig Backup/<Team>/<Folder>/…`. Einzelne Dateien werden direkt in `Downloads` gespeichert. Existiert ein Dateiname bereits, hängt Fig Backup eine Nummer an, statt die Datei zu überschreiben.

## So funktioniert es

Die Figma-REST-API bietet keinen nativen Dateiexport. Fig Backup automatisiert mit einem Browser die Aktion **Save local copy** des Figma-Editors — die Datei auf Ihrer Festplatte ist also genau die Datei, die der Figma-Editor erzeugt. Da dies von der Weboberfläche von Figma abhängt, kann eine künftige Figma-Änderung ein App-Update erforderlich machen.

## Screenshots

| Einrichtungsassistent | Ordner & Dateien |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="Einrichtungsassistent — Schritt Browser-Anmeldung"> | <img src="../screenshots/browse-light.png" alt="Ordner und Dateien eines Teams durchsuchen"> |
| **Download-Manager** | **Dunkelmodus** |
| <img src="../screenshots/download-manager.png" alt="Download-Manager mit laufender Warteschlange"> | <img src="../screenshots/dark-mode.png" alt="Browse-Ansicht im Dunkelmodus"> |

## Datenschutz und Sicherheit

Backups werden auf Ihrem Rechner gespeichert. Fig Backup kommuniziert mit Figma, um auf Ihre Dateien zuzugreifen; Ihre Dateien und Ihr Token werden weder an einen Fig-Backup-Server noch sonstwohin hochgeladen, und es gibt keine Telemetrie.

Ihr Token wird unter `~/Library/Application Support/Fig Backup/token.json` mit Dateirechten `0600` gespeichert. Er liegt nicht im Schlüsselbund und ist nicht zusätzlich verschlüsselt — verwenden Sie kein gemeinsam genutztes Benutzerkonto. Für Skript-Starts kann die Umgebungsvariable `FIGMA_PAT` den Token überschreiben. Details in [SECURITY.md](../../SECURITY.md). Nutzen Sie die App nur mit Dateien, für deren Zugriff Sie berechtigt sind.

## Hilfe und Mitwirken

Probleme bei Installation, Anmeldung oder Download? Lesen Sie die [Fehlerbehebung](../TROUBLESHOOTING.md). Fehlerberichte und Beiträge sind willkommen; siehe [CONTRIBUTING.md](../../CONTRIBUTING.md).

Fig Backup ist ein unabhängiges Projekt und steht in keiner Verbindung zu Figma. Veröffentlicht unter der [MIT-Lizenz](../../LICENSE).

## Spenden

Wenn Fig Backup Ihnen Zeit spart, unterstützen Sie die Entwicklung mit Bitcoin:

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="Bitcoin-Spenden-QR-Code" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> Diese Datei ist eine Übersetzung. Maßgeblich ist das [englische README](../../README.md).
