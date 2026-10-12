# SimpleGraphic Korean bitmap cache build

The PoB runtime contains SimpleGraphic 2.5.4 (`3b1a3468223d0ebd4042d6ce76fc6144718ef79b`). The patch in `simplegraphic-hangul-cache.patch` adds a bounded runtime bitmap atlas for Hangul using the bundled `runtime/SimpleGraphic/Fonts/NotoSansKR-Regular.ttf` font. This is a static Regular instance derived from the official Noto Sans KR variable font at weight 400, so the runtime does not depend on variable-font selection. It does not install the font into Windows or replace existing ASCII atlas entries. The font SHA-256 is `CB9DCF8267B39089948E1950B6B2474B7DD1EFAC754A8640DE75A00455EF14AC`.

## Build

Requirements: Git, Visual Studio 2022 with the C++ desktop workload, CMake, and network access for the pinned SimpleGraphic submodules and vcpkg packages.

From the PoB repository root, run:

```powershell
.\tools\build-simplegraphic-hangul-cache.ps1
```

The script checks out tag `v2.5.4`, verifies commit `3b1a3468223d0ebd4042d6ce76fc6144718ef79b`, applies the pinned patch, builds the x64 Release DLL, and writes it to `tools/out/SimpleGraphic.dll`. Copy that DLL to `runtime/SimpleGraphic.dll`, then refresh `manifest.xml` with `python update_manifest.py --in-place`.

The output directory is configurable:

```powershell
.\tools\build-simplegraphic-hangul-cache.ps1 -OutputDirectory C:\pob-agent-build
```

The font is Noto Sans KR from Google Fonts, distributed under the SIL Open Font License 1.1. The corresponding `OFL.txt` is stored beside the font in the runtime assets.
