<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="أيقونة Fig Backup">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <b>العربية</b> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.pt-BR.md">Português</a> · <a href="README.ru.md">Русский</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.zh-CN.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="حالة بناء فرع windows-build"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

<div dir="rtl">

**احفظ نسخًا أصلية من ملفات Figma على حاسوبك.** Fig Backup تطبيق مكتبي مجاني لأجهزة Mac بشريحة Apple Silicon وWindows 10/11. يحفظ ملفات Figma Design بصيغة `.fig`، وملفات FigJam بصيغة `.jam`، وملفات Figma Slides بصيغة `.deck`.

<p align="center">
  <img src="../screenshots/cover.png" alt="غلاف Fig Backup — نسخ احتياطية أصلية من Figma، تطبيق مكتبي مجاني لنظامي macOS وWindows" width="100%">
</p>

## التنزيل

احصل على [**أحدث إصدار**](https://github.com/danialshirali16/Fig-Backup/releases/latest):

| المنصة | التنزيل |
| --- | --- |
| macOS (Apple Silicon) | [انقر هنا](https://github.com/danialshirali16/Fig-Backup/releases/latest)|
| Windows 10/11 (x64) | [انقر هنا](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip)|

يأتي كل إصدار أيضًا مع ملف `SHA256SUMS.txt` يحتوي بصمات التحقق لكلا الملفين.

عند التشغيل الأول، يُنزّل Fig Backup متصفح Chromium (نحو 150 ميغابايت) ليكون متصفح النسخ الاحتياطي. تطبيق macOS غير موقّع، لذا قد تحتاج إلى النقر عليه بزر الفأرة الأيمن واختيار **Open**. لمساعدة في التثبيت، راجع [دليل استكشاف الأخطاء](../TROUBLESHOOTING.md).

## البداية السريعة

1. أنشئ Figma Personal Access Token بصلاحيتَي `folders:read` و`file_metadata:read` (الرموز القديمة بصلاحية `projects:read` تعمل أيضًا).
2. افتح Fig Backup، والصق الرمز، ثم سجّل الدخول إلى Figma في نافذة المتصفح التي يفتحها التطبيق.
3. اختر فريقك. استخدم **Download all**، أو **Select** لاختيار مجلدات وملفات بعينها.

تسجيل الدخول عبر المتصفح مطلوب قبل أول نسخة احتياطية؛ يمكنك تأجيله أثناء الإعداد وسيطلبه التطبيق مجددًا عند الحاجة. بعد ذلك تجري النسخ الاحتياطية في الخلفية.

## ما الذي يُنسخ احتياطيًا؟

- تُحفظ ملفات Figma Design وFigJam وSlides بتنسيقاتها الأصلية:<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="ملفات Figma Design">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="ملفات FigJam">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="ملفات Figma Slides">
- انسخ فريقًا كاملًا بنقرة واحدة، أو استخدم **Select** لاختيار مجلدات وملفات محددة.
- تحافظ النسخ الاحتياطية للمجلدات على بنية الفرق والمجلدات.
- يعرض مدير التنزيلات التقدم مباشرة ويتيح إعادة المحاولة أو الإيقاف أو إلغاء عناصر قائمة الانتظار. تُتخطى أنواع الملفات غير المدعومة ولا تُحتسب في نسبة التقدم.

تذهب النسخ الاحتياطية للفرق والمجلدات إلى `Downloads/Fig Backup/<Team>/<Folder>/…`، بينما تذهب الملفات المفردة مباشرة إلى `Downloads`. إذا كان اسم الملف موجودًا مسبقًا، يضيف Fig Backup رقمًا بدل الكتابة فوقه.

## كيف يعمل؟

لا تتيح REST API في Figma تصديرًا أصليًا للملفات. يستخدم Fig Backup متصفحًا لأتمتة إجراء **Save local copy** في محرر Figma، بحيث يكون الملف الذي يصل إلى قرصك هو الملف ذاته الذي ينتجه محرر Figma. ولأن هذا يعتمد على واجهة Figma على الويب، فقد يستلزم تغيير مستقبلي في Figma تحديث التطبيق.

## لقطات الشاشة

| معالج الإعداد | المجلدات والملفات |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="معالج الإعداد — خطوة تسجيل الدخول عبر المتصفح"> | <img src="../screenshots/browse-light.png" alt="استعراض مجلدات الفريق وملفاته"> |
| **مدير التنزيلات** | **الوضع الداكن** |
| <img src="../screenshots/download-manager.png" alt="نافذة مدير التنزيلات مع قائمة قيد التنفيذ"> | <img src="../screenshots/dark-mode.png" alt="عرض التصفح بالوضع الداكن"> |

## الخصوصية والأمان

تُحفظ النسخ الاحتياطية على حاسوبك. يتواصل Fig Backup مع Figma للوصول إلى ملفاتك، لكنه لا يرفع ملفاتك أو رمزك إلى أي خادم تابع لـ Fig Backup، ولا يجمع أي بيانات تتبع.

يُحفظ الرمز في المسار `~/Library/Application Support/Fig Backup/token.json` بصلاحية `0600`. لا يُخزَّن في keychain النظام ولا يُشفَّر تشفيرًا منفصلًا — لا تستخدم حساب مستخدم مشتركًا. للتشغيل عبر السكربتات يمكن لمتغير البيئة `FIGMA_PAT` أن يحل محله. التفاصيل في [SECURITY.md](../../SECURITY.md). استخدم التطبيق مع الملفات المصرّح لك بالوصول إليها فقط.

## المساعدة والمشاركة

تواجه مشكلة في التثبيت أو تسجيل الدخول أو التنزيل؟ اقرأ [دليل استكشاف الأخطاء](../TROUBLESHOOTING.md). يُرحَّب بتقارير الأخطاء والمساهمات؛ راجع [CONTRIBUTING.md](../../CONTRIBUTING.md).

Fig Backup مشروع مستقل وغير تابع لـ Figma. يُنشر بموجب [رخصة MIT](../../LICENSE).

## التبرع

إذا وفّر لك Fig Backup وقتًا، فيمكنك دعم تطويره بعملة البيتكوين:

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="رمز QR للتبرع بالبيتكوين" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

</div>

> هذا الملف ترجمة؛ النسخة [الإنجليزية](../../README.md) هي المرجع.
