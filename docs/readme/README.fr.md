<p align="center">
  <img src="../screenshots/icon-256.png" width="88" alt="Icône Fig Backup">
</p>

<h1 align="center">Fig Backup</h1>

<p align="center">
  <a href="../../README.md">English</a> · <a href="README.fa.md">فارسی</a> · <a href="README.ar.md">العربية</a> · <a href="README.de.md">Deutsch</a> · <a href="README.es.md">Español</a> · <b>Français</b> · <a href="README.pt-BR.md">Português</a> · <a href="README.ru.md">Русский</a> · <a href="README.tr.md">Türkçe</a> · <a href="README.zh-CN.md">中文</a> · <a href="README.ja.md">日本語</a>
</p>

<p align="center">
  <a href="../../LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows-blue">
  <a href="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml?query=branch%3Awindows-build" title="Statut de build de la branche windows-build"><img alt="Windows build (windows-build branch)" src="https://github.com/danialshirali16/Fig-Backup/actions/workflows/windows-build.yml/badge.svg?branch=windows-build"></a>
</p>

**Enregistrez des copies natives de vos fichiers Figma sur votre ordinateur.** Fig Backup est une application de bureau gratuite pour Mac Apple Silicon et Windows 10/11. Elle enregistre les fichiers Figma Design en `.fig`, les fichiers FigJam en `.jam` et les fichiers Figma Slides en `.deck`.

<p align="center">
  <img src="../screenshots/cover.png" alt="Couverture de Fig Backup — sauvegardes natives depuis Figma, application de bureau gratuite pour macOS et Windows" width="100%">
</p>

## Télécharger

Obtenez la [**dernière version**](https://github.com/danialshirali16/Fig-Backup/releases/latest) :

| Plateforme | Téléchargement |
| --- | --- |
| macOS (Apple Silicon) | [`Fig-Backup-macOS.zip`](https://github.com/danialshirali16/Fig-Backup/releases/latest) — le nom du fichier inclut le numéro de version |
| Windows 10/11 (x64) | [`Fig-Backup-Windows-x64.zip`](https://github.com/danialshirali16/Fig-Backup/releases/latest/download/Fig-Backup-Windows-x64.zip) — téléchargement direct |

Chaque version est également livrée avec un fichier `SHA256SUMS.txt` contenant les sommes de contrôle des deux fichiers.

Au premier lancement, Fig Backup télécharge Chromium (environ 150 Mo) comme navigateur de sauvegarde. L'application macOS n'est pas signée : vous devrez peut-être faire un clic droit dessus puis choisir **Open**. Pour toute aide à l'installation, consultez le [guide de dépannage](../TROUBLESHOOTING.md).

## Premiers pas

1. Créez un Figma Personal Access Token avec les autorisations `folders:read` et `file_metadata:read` (les anciens tokens avec `projects:read` fonctionnent aussi).
2. Ouvrez Fig Backup, collez le token et connectez-vous à Figma dans la fenêtre de navigateur ouverte par l'application.
3. Choisissez une équipe. Utilisez **Download all**, ou **Select** pour choisir des dossiers et des fichiers précis.

La connexion via le navigateur est requise avant la première sauvegarde ; vous pouvez la reporter pendant la configuration et l'application vous le redemandera au besoin. Ensuite, les sauvegardes s'exécutent en arrière-plan.

## Ce qui est sauvegardé

- Les fichiers Figma Design, FigJam et Slides sont enregistrés dans leur format natif :<br>
  <img src="../screenshots/figma-file-design.png" height="20" alt="Fichiers Figma Design">
  <img src="../screenshots/figma-file-figjam.png" height="20" alt="Fichiers FigJam">
  <img src="../screenshots/figma-file-slides.png" height="20" alt="Fichiers Figma Slides">
- Sauvegardez une équipe entière en un clic, ou utilisez **Select** pour choisir des dossiers et des fichiers.
- Les sauvegardes de dossiers conservent la structure des équipes et des dossiers.
- Le gestionnaire de téléchargement affiche la progression en direct et permet de réessayer, d'interrompre ou d'annuler les éléments en file. Les types de fichiers non pris en charge sont ignorés et ne comptent pas dans le pourcentage de progression.

Les sauvegardes d'équipes et de dossiers vont dans `Downloads/Fig Backup/<Team>/<Folder>/…`. Les fichiers seuls vont directement dans `Downloads`. Si un nom de fichier existe déjà, Fig Backup ajoute un numéro au lieu de l'écraser.

## Fonctionnement

L'API REST de Figma ne fournit pas d'export natif des fichiers. Fig Backup utilise un navigateur pour automatiser l'action **Save local copy** de l'éditeur Figma : le fichier qui arrive sur votre disque est donc exactement celui que produit l'éditeur Figma. Comme cela dépend de l'interface web de Figma, une future modification de Figma pourra nécessiter une mise à jour de l'application.

## Captures d'écran

| Assistant de configuration | Dossiers et fichiers |
| --- | --- |
| <img src="../screenshots/setup-wizard.png" alt="Assistant de configuration — étape de connexion via le navigateur"> | <img src="../screenshots/browse-light.png" alt="Parcourir les dossiers et fichiers d'une équipe"> |
| **Gestionnaire de téléchargement** | **Mode sombre** |
| <img src="../screenshots/download-manager.png" alt="Gestionnaire de téléchargement avec une file en cours"> | <img src="../screenshots/dark-mode.png" alt="Vue de navigation en mode sombre"> |

## Confidentialité et sécurité

Les sauvegardes sont enregistrées sur votre ordinateur. Fig Backup communique avec Figma pour accéder à vos fichiers et ne téléverse ni vos fichiers ni votre token vers un serveur Fig Backup ; aucune télémétrie n'est collectée.

Votre token est stocké dans `~/Library/Application Support/Fig Backup/token.json` avec les permissions `0600`. Il n'est pas conservé dans le trousseau système et n'est pas chiffré séparément — n'utilisez pas de compte utilisateur partagé. Pour les lancements par script, la variable d'environnement `FIGMA_PAT` peut le remplacer. Voir [SECURITY.md](../../SECURITY.md) pour plus de détails. N'utilisez l'application qu'avec des fichiers que vous êtes autorisé à consulter.

## Aide et contribution

Des problèmes d'installation, de connexion ou de téléchargement ? Lisez le [guide de dépannage](../TROUBLESHOOTING.md). Les rapports de bugs et les contributions sont les bienvenus ; voir [CONTRIBUTING.md](../../CONTRIBUTING.md).

Fig Backup est un projet indépendant, sans affiliation avec Figma. Publié sous [licence MIT](../../LICENSE).

## Faire un don

Si Fig Backup vous fait gagner du temps, soutenez son développement en Bitcoin :

<p align="center">
  <img src="../screenshots/donate-qr.png" alt="Code QR de don en Bitcoin" width="180"><br>
  <code>bc1qf9dufwjyzp7u56lysgn2a0n2956y6xm5dzq6q4</code>
</p>

> Ce fichier est une traduction. Le [README en anglais](../../README.md) fait foi.
