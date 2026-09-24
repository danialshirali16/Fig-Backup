<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Icono de Fig Backup">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <a href="README.de.md">Deutsch</a> · <b>Español</b> · <a href="README.fr.md">Français</a> · <a href="README.pt-BR.md">Português</a> · <a href="README.ru.md">Русский</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.zh-CN.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="Estado de compilación de la rama windows-build"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**Guarda copias nativas de tus archivos de Figma en tu ordenador.** Fig Backup es una aplicación de escritorio gratuita para Mac con Apple Silicon y Windows 10/11. Guarda los archivos de Figma Design como `.fig`, los de FigJam como `.jam` y los de Figma Slides como `.deck`.

<p align="center">
  <img src="../screenshots/cover.png" alt="Portada de Fig Backup — copias nativas de Figma, aplicación de escritorio gratuita para macOS y Windows" width="100%">
</p>

## Descargar

Obtén la [**última versión**](https://github.com/danialshirali16/Fig-Backup/releases/latest):

| Plataforma | Descarga |
| --- | --- |
| macOS (Apple Silicon) | [`Fig-Backup-macOS.zip`](https://github.com/danialshirali16/Fig-Backup/releases/latest) — el nombre del archivo incluye la versión |
| Windows 10/11 (x64) | [`Fig-Backup-Windows-x64.zip`](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip) — descarga directa |

Cada versión también incluye un archivo `SHA256SUMS.txt` con las sumas de comprobación de ambos archivos.

Al abrirse por primera vez, Fig Backup descarga Chromium (unos 150 MB) como navegador de copias de seguridad. La app de macOS no está firmada; es posible que tengas que hacer clic derecho sobre ella y elegir **Open**. Para ayuda con la instalación, consulta [Solución de problemas](../TROUBLESHOOTING.md).

## Primeros pasos

1. Crea un Figma Personal Access Token con los permisos `folders:read` y `file_metadata:read` (los tokens antiguos con `projects:read` también funcionan).
2. Abre Fig Backup, pega el token e inicia sesión en Figma en la ventana del navegador que abre la app.
3. Elige un equipo. Usa **Download all**, o **Select** para elegir carpetas y archivos concretos.

Iniciar sesión en el navegador es necesario antes de la primera copia de seguridad; puedes posponerlo durante la configuración y la app volverá a pedirlo cuando haga falta. Después, las copias de seguridad se ejecutan en segundo plano.

## ¿Qué se guarda?

- Los archivos de Figma Design, FigJam y Slides se guardan en su formato nativo:<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Archivos de Figma Design">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="Archivos de FigJam">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Archivos de Figma Slides">
- Haz una copia de todo un equipo con un clic, o usa **Select** para elegir carpetas y archivos concretos.
- Las copias de carpetas conservan la estructura de equipos y carpetas.
- El gestor de descargas muestra el progreso en vivo y permite reintentar, detener o cancelar los elementos en cola. Los tipos de archivo no compatibles se omiten y no cuentan en el porcentaje de progreso.

Las copias de equipos y carpetas van a `Downloads/Fig Backup/<Team>/<Folder>/…`. Los archivos individuales van directamente a `Downloads`. Si ya existe un nombre de archivo, Fig Backup añade un número en lugar de sobrescribirlo.

## Cómo funciona

La API REST de Figma no ofrece exportaciones nativas de archivos. Fig Backup usa un navegador para automatizar la acción **Save local copy** del editor de Figma, de modo que lo que llega a tu disco es el mismo archivo que produce el editor de Figma. Como esto depende de la interfaz web de Figma, un cambio futuro de Figma puede requerir una actualización de la app.

## Capturas de pantalla

| Asistente de configuración | Carpetas y archivos |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="Asistente de configuración — paso de inicio de sesión en el navegador"> | <img src="../screenshots/browse-light.png" alt="Explorar las carpetas y archivos de un equipo"> |
| **Gestor de descargas** | **Modo oscuro** |
| <img src="../screenshots/download-manager.png" alt="Gestor de descargas con una cola en marcha"> | <img src="../screenshots/dark-mode.png" alt="Vista de exploración en modo oscuro"> |

## Privacidad y seguridad

Las copias de seguridad se guardan en tu ordenador. Fig Backup se comunica con Figma para acceder a tus archivos y no sube tus archivos ni tu token a ningún servidor de Fig Backup, y no recopila telemetría.

Tu token se guarda en `~/Library/Application Support/Fig Backup/token.json` con permisos `0600`. No se guarda en el llavero del sistema ni está cifrado por separado — no uses una cuenta de usuario compartida. Para lanzamientos por script, la variable de entorno `FIGMA_PAT` puede sustituirlo. Consulta [SECURITY.md](../../SECURITY.md) para más detalles. Usa la app solo con archivos a los que tengas autorización de acceso.

## Ayuda y contribuir

¿Problemas para instalar, iniciar sesión o descargar? Lee [Solución de problemas](../TROUBLESHOOTING.md). Los informes de errores y las contribuciones son bienvenidos; ver [CONTRIBUTING.md](../../CONTRIBUTING.md).

Fig Backup es un proyecto independiente y no está afiliado a Figma. Se publica bajo la [Licencia MIT](../../LICENSE).

## Donar

Si Fig Backup te ahorra tiempo, apoya su desarrollo con Bitcoin:

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="Código QR de donación en Bitcoin" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> Este archivo es una traducción. La versión de referencia es el [README en inglés](../../README.md).
