# Shipping StickyNotes

This is the checklist for turning the source into something you can hand to
customers. Everything here is double-click-and-go where possible.

## 1. Build the app (`build.bat`)

Double-click **`build.bat`**. It installs the dependencies and bundles
everything into a single file:

```
dist\StickyNotes.exe
```

That one file is the whole app — customers need no Python and nothing else
installed. Notes are saved per-user in `%APPDATA%\StickyNotes`, so it works no
matter where it's installed.

## 2. Build the installer (`build_installer.bat`)

Double-click **`build_installer.bat`**. It uses [Inno Setup] to produce:

```
installer\StickyNotes_Setup.exe
```

This is the friendlier thing to give customers: it installs to their user
folder (no admin needed), adds a Start Menu shortcut, and offers optional
desktop / run-at-login shortcuts, plus a clean uninstaller in
Add/Remove Programs. If Inno Setup isn't installed, the script installs it via
`winget` the first time (you may see one Windows "allow this app" prompt —
click **Yes**).

[Inno Setup]: https://jrsoftware.org/isinfo.php

## 3. Code sign (`sign.bat`) — removes the SmartScreen warning

Unsigned apps trigger Windows SmartScreen ("Windows protected your PC /
unknown publisher") on a customer's first run. To remove that you need a
**code-signing certificate**:

- **OV (standard) certificate** — ~$100–200/year from a certificate authority
  (Sectigo, DigiCert, SSL.com, etc.). Cheapest; SmartScreen trust builds up
  over time / downloads.
- **EV certificate** — ~$250–400/year; gives instant SmartScreen trust but
  requires a hardware token.

Once you have the certificate as a `.pfx` file, drop it in this folder and run:

```
sign.bat mycert.pfx YOUR_PFX_PASSWORD
```

That signs both `dist\StickyNotes.exe` and `installer\StickyNotes_Setup.exe`.
Sign **after** building and **before** distributing. (`signtool.exe` comes with
the Windows SDK; the script will point you to it if it's missing.)

Until it's signed, customers can still run it by clicking
**More info → Run anyway** on the SmartScreen dialog.

## 4. Distribute

Give customers `installer\StickyNotes_Setup.exe` (preferred) or the bare
`dist\StickyNotes.exe`. Good places to host it: a GitHub Release on this repo,
your own site, or a storefront like Gumroad/itch.io.

## Rebuilding a new version

1. Bump the version in `app.py` (`APP_VERSION`), `version_info.txt`, and
   `StickyNotes.iss` (`MyAppVersion`).
2. Run `build.bat`, then `build_installer.bat`, then `sign.bat`.
