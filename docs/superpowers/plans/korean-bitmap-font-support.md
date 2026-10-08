# Korean Bitmap Font Support Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to carry out this plan task-by-task.

**Goal:** Make Korean text render throughout PoB using cached bitmap glyphs from a font bundled with the application, without relying on fonts installed on Windows.

**Architecture:** Extend the upstream SimpleGraphic font renderer with a Unicode glyph cache. Keep existing `.tgf` atlases for the glyphs they already contain. For missing Hangul code points, rasterize from bundled Noto Sans CJK KR into bounded GPU bitmap atlas pages. Route drawing, measurement, and cursor indexing through the same glyph lookup. Store a reproducible upstream source patch and build instructions in the PoB repository, then package the resulting DLL, font resource, license, and manifest hashes.

**Tech Stack:** C++23, Windows GDI rasterization from an embedded font resource, OpenGL texture atlas updates, Noto Sans CJK KR (SIL OFL 1.1), PowerShell build/package tooling, PoB Lua runtime.

---

### Task 1: Pin the native renderer source and add a reproducible patch workflow

**Files:**
- Create: `tools/simplegraphic-hangul-cache.patch`
- Create: `tools/build-simplegraphic-hangul-cache.ps1`
- Create: `tools/simplegraphic-hangul-cache.md`

**Steps:**
1. Record the exact upstream SimpleGraphic commit currently represented by `runtime/SimpleGraphic.dll` where available, and the upstream source commit selected for the patch.
2. Add the minimal patch against upstream source instead of committing an opaque DLL-only change.
3. Add a PowerShell script that checks out the pinned source, applies the patch, configures the supported x64 Windows build, and emits `SimpleGraphic.dll` to a staging directory.
4. Document required compiler/vcpkg prerequisites, source revision, patch application, output location, and the manual packaging command.

**Acceptance:** A clean checkout can reproduce the modified renderer build from the pinned upstream source and patch.

### Task 2: Add a bundled, licensed Korean font resource

**Files:**
- Add: `runtime/SimpleGraphic/Fonts/NotoSansCJKkr-Regular.otf` (or a smaller official KR subset proven to cover the required scripts)
- Add: `runtime/SimpleGraphic/Fonts/NotoSansCJKkr-Bold.otf` (if a separate bold face is included)
- Add: `runtime/SimpleGraphic/Fonts/OFL.txt`
- Modify: `manifest.xml`

**Steps:**
1. Select an official Korean subset from Noto CJK that includes the full Hangul syllable block, modern jamo, and Korean punctuation.
2. Include its license and required notices alongside the font resource.
3. Add font and license files to the PoB update manifest with generated SHA-1 hashes.
4. Ensure the font can be loaded from the PoB runtime path without installing it into Windows.

**Acceptance:** The font file has the required Korean coverage, is loaded from the application bundle, and its license is included in the package.

### Task 3: Implement the Unicode bitmap glyph cache in SimpleGraphic

**Upstream files:**
- Modify: `engine/render/r_font.cpp`
- Modify: `engine/render/r_font.h`
- Modify: upstream texture/render files only if required to upload atlas subregions safely

**Steps:**
1. Preserve the current 128 ASCII entries and lookup behavior exactly.
2. Add a font resource loader for the bundled Korean font faces; rasterize requested Unicode Hangul glyphs to transparent bitmap data at the requested render height.
3. Add a codepoint-and-style glyph cache with atlas pages, metrics, advance widths, and bearings. Use the regular face by default and the bold face for existing bold font styles.
4. Set a fixed cache memory budget, track page use, and evict least-recently-used pages only at safe frame boundaries. Retain tofu rendering when the code point is unsupported or rasterization fails.
5. Update `StringWidthInternal`, `StringCursorInternal`, and `DrawTextLine` to use one shared glyph lookup path so mixed ASCII/Korean text has consistent rendering, wrapping, alignment, and cursor indexes.
6. Preserve color escapes, tabs, newlines, and existing placeholder behavior for unsupported scripts.
7. Add the patch and its revision metadata to the PoB build workflow created in Task 1.

**Acceptance:** Existing ASCII output and font files remain unchanged; Korean glyphs display as bitmap textures in all PoB fonts and supported sizes; measured widths and cursor positions match the rendered text; cache memory remains within its configured bound.

### Task 4: Build and package the updated runtime

**Files:**
- Replace: `runtime/SimpleGraphic.dll`
- Modify: `manifest.xml`
- Modify: `tools/build-simplegraphic-hangul-cache.ps1` if needed

**Steps:**
1. Build the patched SimpleGraphic x64 Windows runtime from the pinned source.
2. Copy the built DLL into `runtime/` and add its SHA-1 entry to `manifest.xml`.
3. Confirm the bundled font, OFL notice, and DLL are included in the runtime package and updater manifest.
4. Keep all unrelated changes, including the existing untracked `qa_tmp/`, out of the commit.

**Acceptance:** PoB loads the new runtime and can load the bundled Korean font without modifying the user's installed fonts.

### Task 5: Manually verify Korean rendering across the UI

**Files:** No additional files unless a defect is found.

**Steps:**
1. Launch the packaged PoB build with the agent chat overlay and display mixed Korean/ASCII, all-Hangul, punctuation, and multiline messages.
2. Check text at several UI sizes, including small controls and large headings; confirm spacing, clipping, color escape handling, and alignment.
3. Type Korean in an edit control and verify caret movement, selection, hit testing, width, and wrapping.
4. Exercise a long string that crosses atlas pages and confirm cache eviction does not corrupt visible text during the frame.
5. Verify unsupported Hanja still displays a `U+XXXX` placeholder and that ASCII-only UI looks unchanged.
6. Run no test suite unless the user requests it; use the manual UI checks above for this request.

**Acceptance:** Korean is readable across the PoB UI without an installed Korean font; drawing, measurement, cursor behavior, and existing ASCII appearance are correct.
