<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Fig Backup simgesi">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <a href="README.fr.md">Français</a> · <a href="README.pt-BR.md">Português</a> · <a href="README.ru.md">Русский</a> · <b>Türkçe</b> · <a href="README.zh-CN.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="windows-build dalının derleme durumu"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**Figma dosyalarınızın özgün kopyalarını bilgisayarınıza kaydedin.** Fig Backup, Apple Silicon Mac'ler ve Windows 10/11 için ücretsiz bir masaüstü uygulamasıdır. Figma Design dosyalarını `.fig`, FigJam dosyalarını `.jam`, Figma Slides dosyalarını `.deck` olarak kaydeder.

<p align="center">
  <img src="../screenshots/cover.png" alt="Fig Backup kapağı — Figma'dan özgün yedekler, macOS ve Windows için ücretsiz masaüstü uygulaması" width="100%">
</p>

## İndir

[**En son sürümü**](https://github.com/danialshirali16/Fig-Backup/releases/latest) edinin:

| Platform | İndirme |
| --- | --- |
| macOS (Apple Silicon) | [`Fig-Backup-macOS.zip`](https://github.com/danialshirali16/Fig-Backup/releases/latest) — dosya adı sürüm numarasını içerir |
| Windows 10/11 (x64) | [`Fig-Backup-Windows-x64.zip`](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip) — doğrudan indirme |

Her sürüm, her iki dosyanın sağlama toplamlarını içeren bir `SHA256SUMS.txt` dosyası da içerir.

İlk açılışta Fig Backup, yedekleme tarayıcısı için Chromium'ı (~150 MB) indirir. macOS uygulaması imzasızdır; sağ tıklayıp **Open** seçmeniz gerekebilir. Kurulum yardımı için [Sorun Giderme](../TROUBLESHOOTING.md) bölümüne bakın.

## Hızlı başlangıç

1. `folders:read` ve `file_metadata:read` izinleriyle bir Figma Personal Access Token oluşturun (`projects:read` içeren eski tokenlar da çalışır).
2. Fig Backup'ı açın, token'ı yapıştırın ve uygulamanın açtığı tarayıcı penceresinde Figma'ya giriş yapın.
3. Bir ekip seçin. **Download all** ile her şeyi alın ya da **Select** ile belirli klasör ve dosyaları seçin.

İlk yedeklemeden önce tarayıcı girişi gerekir; kurulum sırasında erteleyebilirsiniz, uygulama gerektiğinde yeniden sorar. Sonrasında yedeklemeler arka planda çalışır.

## Neler yedeklenir?

- Figma Design, FigJam ve Slides dosyaları kendi özgün biçimlerinde kaydedilir:<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Figma Design dosyaları">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="FigJam dosyaları">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Figma Slides dosyaları">
- Tek tıkla tüm bir ekibi yedekleyin ya da **Select** ile belirli klasör ve dosyaları seçin.
- Klasör yedekleri ekip ve klasör yapısını korur.
- İndirme yöneticisi canlı ilerlemeyi gösterir; kuyruktaki öğeleri yeniden deneyebilir, durdurabilir veya iptal edebilirsiniz. Desteklenmeyen dosya türleri atlanır ve ilerleme yüzdesine sayılmaz.

Ekip ve klasör yedekleri `Downloads/Fig Backup/<Team>/<Folder>/…` altına gider. Tek dosyalar doğrudan `Downloads` klasörüne kaydedilir. Aynı adda bir dosya varsa Fig Backup üzerine yazmak yerine bir numara ekler.

## Nasıl çalışır?

Figma REST API'si özgün dosya dışa aktarımı sunmaz. Fig Backup bir tarayıcıyla Figma düzenleyicisinin **Save local copy** işlemini otomatikleştirir; diskinize ulaşan dosya, Figma düzenleyicisinin ürettiği dosyanın ta kendisidir. Bu, Figma'nın web arayüzüne bağlı olduğundan, Figma'nın ileride yapacağı bir değişiklik uygulama güncellemesi gerektirebilir.

## Ekran görüntüleri

| Kurulum sihirbazı | Klasörler ve dosyalar |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="Kurulum sihirbazı — tarayıcı girişi adımı"> | <img src="../screenshots/browse-light.png" alt="Bir ekibin klasörlerine ve dosyalarına göz atma"> |
| **İndirme yöneticisi** | **Koyu tema** |
| <img src="../screenshots/download-manager.png" alt="Çalışan kuyrukla indirme yöneticisi"> | <img src="../screenshots/dark-mode.png" alt="Koyu temada görüntüleme ekranı"> |

## Gizlilik ve güvenlik

Yedekler bilgisayarınızda saklanır. Fig Backup dosyalarınıza erişmek için Figma ile iletişim kurar; dosyalarınızı veya token'ınızı hiçbir Fig Backup sunucusuna yüklemez ve telemetri toplamaz.

Token'ınız `~/Library/Application Support/Fig Backup/token.json` yolunda `0600` izinleriyle saklanır. Sistem anahtar zincirinde tutulmaz ve ayrıca şifrelenmez — paylaşılan bir kullanıcı hesabı kullanmayın. Betikle başlatma için `FIGMA_PAT` ortam değişkeni kullanılabilir. Ayrıntılar için [SECURITY.md](../../SECURITY.md). Uygulamayı yalnızca erişim yetkiniz olan dosyalarla kullanın.

## Yardım ve katkı

Kurulum, giriş veya indirme sorunu mu yaşıyorsunuz? [Sorun Giderme](../TROUBLESHOOTING.md) bölümünü okuyun. Hata raporları ve katkılar memnuniyetle karşılanır; bkz. [CONTRIBUTING.md](../../CONTRIBUTING.md).

Fig Backup bağımsız bir projedir ve Figma ile bağlantılı değildir. [MIT Lisansı](../../LICENSE) ile yayımlanır.

## Bağış

Fig Backup zaman kazandırıyorsa gelişimini Bitcoin ile destekleyebilirsiniz:

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="Bitcoin bağış QR kodu" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> Bu dosya bir çeviridir. Yetkili sürüm [İngilizce README](../../README.md) dosyasıdır.
