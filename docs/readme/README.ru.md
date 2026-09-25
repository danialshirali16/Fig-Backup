<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Значок Fig Backup">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.pt-BR.md">Português</a> · <b>Русский</b> · <a href="README.tr.md">Türkçe</a> · <a href="README.zh-CN.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="Статус сборки ветки windows-build"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**Сохраняйте нативные копии своих файлов Figma на компьютер.** Fig Backup — бесплатное настольное приложение для Mac на Apple Silicon и Windows 10/11. Оно сохраняет файлы Figma Design как `.fig`, файлы FigJam как `.jam`, а файлы Figma Slides как `.deck`.

<p align="center">
  <img src="../screenshots/cover.png" alt="Обложка Fig Backup — нативные резервные копии из Figma, бесплатное настольное приложение для macOS и Windows" width="100%">
</p>

## Загрузка

Возьмите [**последний релиз**](https://github.com/danialshirali16/Fig-Backup/releases/latest):

| Платформа | Загрузка |
| --- | --- |
| macOS (Apple Silicon) | [Нажмите здесь](https://github.com/danialshirali16/Fig-Backup/releases/latest)|
| Windows 10/11 (x64) | [Нажмите здесь](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip)|

Каждый релиз также включает файл `SHA256SUMS.txt` с контрольными суммами обоих файлов.

При первом запуске Fig Backup скачивает Chromium (около 150 МБ) в качестве резервного браузера. Приложение macOS не подписано — возможно, потребуется щёлкнуть по нему правой кнопкой мыши и выбрать **Open**. С установкой поможет [руководство по устранению неполадок](../TROUBLESHOOTING.md).

## Начало работы

1. Создайте Figma Personal Access Token с разрешениями `folders:read` и `file_metadata:read` (старые токены с `projects:read` тоже работают).
2. Откройте Fig Backup, вставьте токен и войдите в Figma в открывшемся окне браузера.
3. Выберите команду. Нажмите **Download all** или используйте **Select**, чтобы выбрать конкретные папки и файлы.

Вход через браузер требуется перед первым резервным копированием; его можно отложить при настройке — приложение спросит снова, когда понадобится. После этого резервное копирование идёт в фоне.

## Что сохраняется

- Файлы Figma Design, FigJam и Slides сохраняются в их родных форматах:<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Файлы Figma Design">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="Файлы FigJam">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Файлы Figma Slides">
- Резервируйте всю команду одним кликом или выберите **Select** для конкретных папок и файлов.
- При резервном копировании папок структура команд и папок сохраняется.
- Менеджер загрузок показывает прогресс в реальном времени и позволяет повторять, останавливать и отменять элементы очереди. Неподдерживаемые типы файлов пропускаются и не учитываются в проценте прогресса.

Резервные копии команд и папок попадают в `Downloads/Fig Backup/<Team>/<Folder>/…`. Отдельные файлы сохраняются прямо в `Downloads`. Если имя файла уже существует, Fig Backup добавляет номер, а не перезаписывает файл.

## Как это работает

REST API Figma не предоставляет нативный экспорт файлов. Fig Backup использует браузер, чтобы автоматизировать действие **Save local copy** в редакторе Figma, — на диск попадает тот же файл, который создаёт редактор Figma. Поскольку это зависит от веб-интерфейса Figma, будущее изменение Figma может потребовать обновления приложения.

## Скриншоты

| Мастер настройки | Папки и файлы |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="Мастер настройки — шаг входа через браузер"> | <img src="../screenshots/browse-light.png" alt="Просмотр папок и файлов команды"> |
| **Менеджер загрузок** | **Тёмная тема** |
| <img src="../screenshots/download-manager.png" alt="Менеджер загрузок с идущей очередью"> | <img src="../screenshots/dark-mode.png" alt="Экран просмотра в тёмной теме"> |

## Конфиденциальность и безопасность

Резервные копии сохраняются на вашем компьютере. Fig Backup обращается к Figma для доступа к вашим файлам и не загружает ваши файлы или токен на какие-либо серверы Fig Backup; телеметрии нет.

Токен хранится в `~/Library/Application Support/Fig Backup/token.json` с правами `0600`. Он не хранится в системной связке ключей и не имеет отдельного шифрования — не используйте общий аккаунт пользователя. Для запуска из скриптов переменная окружения `FIGMA_PAT` может заменить его. Подробнее в [SECURITY.md](../../SECURITY.md). Используйте приложение только с файлами, доступ к которым вам разрешён.

## Помощь и участие

Проблемы с установкой, входом или загрузкой? Читайте [руководство по устранению неполадок](../TROUBLESHOOTING.md). Сообщения об ошибках и вклад приветствуются; см. [CONTRIBUTING.md](../../CONTRIBUTING.md).

Fig Backup — независимый проект, не связанный с Figma. Распространяется по [лицензии MIT](../../LICENSE).

## Поддержать разработку

Если Fig Backup экономит ваше время, поддержите разработку биткоином:

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="QR-код для пожертвований в биткоинах" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> Этот файл — перевод. Оригиналом является [README на английском](../../README.md).
