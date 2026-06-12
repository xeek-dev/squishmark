# Changelog

## [0.3.0](https://github.com/xeek-dev/squishmark/compare/v0.2.0...v0.3.0) (2026-06-12)


### Features

* **search:** add server-side search with navbar ui across themes ([#101](https://github.com/xeek-dev/squishmark/issues/101)) ([bd39bab](https://github.com/xeek-dev/squishmark/commit/bd39bab9b16c2d705f845bb35ef0c300451a0c5a))

## [0.2.0](https://github.com/xeek-dev/squishmark/compare/v0.1.0...v0.2.0) (2026-06-11)


### Features

* add blue-tech theme and multi-theme support ([#15](https://github.com/xeek-dev/squishmark/issues/15)) ([4c62511](https://github.com/xeek-dev/squishmark/commit/4c6251167a8cbe217dce1d1b741e86953876c9bd))
* add dev mode auth bypass ([#23](https://github.com/xeek-dev/squishmark/issues/23)) ([460ac9c](https://github.com/xeek-dev/squishmark/commit/460ac9cb4abc08e28f77d1816b14e7326b650f4c))
* add favicon support for content repositories ([#2](https://github.com/xeek-dev/squishmark/issues/2)) ([4387708](https://github.com/xeek-dev/squishmark/commit/43877088d6f742de9c2881d41391f63df9ecd2c2))
* add language labels to code blocks ([#22](https://github.com/xeek-dev/squishmark/issues/22)) ([c9252ad](https://github.com/xeek-dev/squishmark/commit/c9252ad0aadadb91a69a51387d0720f741b84fb9))
* add per-post author support ([#24](https://github.com/xeek-dev/squishmark/issues/24)) ([3b96e6f](https://github.com/xeek-dev/squishmark/commit/3b96e6f90a80d48d1ef128e9dbec99b286486ca8))
* add relative image URL rewriting for markdown content ([#4](https://github.com/xeek-dev/squishmark/issues/4)) ([31b5370](https://github.com/xeek-dev/squishmark/commit/31b5370342d84b5cbdf4c806a2555c7f1c6d8cc2))
* add terminal theme with pixel art and configurable backgrounds ([#29](https://github.com/xeek-dev/squishmark/issues/29)) ([d80e257](https://github.com/xeek-dev/squishmark/commit/d80e2573b293689c63387b8eed318fa1943b92b9))
* **admin:** add CSRF protection to mutation endpoints ([#79](https://github.com/xeek-dev/squishmark/issues/79)) ([f14b16b](https://github.com/xeek-dev/squishmark/commit/f14b16b92cf3fcb565b7397e2a55b3050e678d55))
* **admin:** notes edit/delete UI + fix broken create flow ([#71](https://github.com/xeek-dev/squishmark/issues/71)) ([#78](https://github.com/xeek-dev/squishmark/issues/78)) ([338deb0](https://github.com/xeek-dev/squishmark/commit/338deb0de76c8a59e1413f92ff63d0d331b1d06b))
* **analytics:** filter bots and non-content endpoints from page-view tracking ([#77](https://github.com/xeek-dev/squishmark/issues/77)) ([#82](https://github.com/xeek-dev/squishmark/issues/82)) ([821ee65](https://github.com/xeek-dev/squishmark/commit/821ee6555d859bd3b376252e50a8cc0b52d429f9))
* **content:** add featured post and page support ([#51](https://github.com/xeek-dev/squishmark/issues/51)) ([72ad087](https://github.com/xeek-dev/squishmark/commit/72ad08736069a81cd831a8fa65708607183b65a3))
* **content:** add post series support via frontmatter ([#92](https://github.com/xeek-dev/squishmark/issues/92)) ([c5af304](https://github.com/xeek-dev/squishmark/commit/c5af30482e42fd4d8471431093cf4950edf13c46))
* **content:** expose auto-generated TOC as post.toc ([#84](https://github.com/xeek-dev/squishmark/issues/84)) ([90c47c6](https://github.com/xeek-dev/squishmark/commit/90c47c6dc771328fad95c62b95bbf1e7600f4890))
* **dx:** add theme hot reload for development ([#52](https://github.com/xeek-dev/squishmark/issues/52)) ([32109e1](https://github.com/xeek-dev/squishmark/commit/32109e13c598d8ad62f7db1e7431066409013b1e))
* **nav:** add dynamic navbar with page visibility support ([#50](https://github.com/xeek-dev/squishmark/issues/50)) ([e292b4b](https://github.com/xeek-dev/squishmark/commit/e292b4b089096662b54fc3853c4e218beae94ab5))
* **seo:** add Atom feed, Open Graph meta tags, and reading time ([#53](https://github.com/xeek-dev/squishmark/issues/53)) ([9cff0ed](https://github.com/xeek-dev/squishmark/commit/9cff0edda57433dfd30475a427eb09de4c056063))
* **seo:** add canonical URLs to all pages ([#66](https://github.com/xeek-dev/squishmark/issues/66)) ([7251c5a](https://github.com/xeek-dev/squishmark/commit/7251c5a35dc884c45bd30508406523b4cf9cd316))
* **seo:** add sitemap.xml and robots.txt generation ([#48](https://github.com/xeek-dev/squishmark/issues/48), [#60](https://github.com/xeek-dev/squishmark/issues/60)) ([#76](https://github.com/xeek-dev/squishmark/issues/76)) ([119df90](https://github.com/xeek-dev/squishmark/commit/119df908c482887b3315a7c09acf209ece6cfaf0))
* **theme:** redesign default theme — clean minimal, light/dark mode, Pomeranian orange accent ([#69](https://github.com/xeek-dev/squishmark/issues/69)) ([cca7ac5](https://github.com/xeek-dev/squishmark/commit/cca7ac5f97c21c9934facc4680d14179ccb3d7da))


### Bug Fixes

* **ci:** add --diff flag to ruff format for better error output ([#3](https://github.com/xeek-dev/squishmark/issues/3)) ([e5aea12](https://github.com/xeek-dev/squishmark/commit/e5aea12979f76d1bac4de4fce65c1c497cfad0f8))
* **docs:** update playwright cache-busting and enforce conventional commits ([#34](https://github.com/xeek-dev/squishmark/issues/34)) ([57fe50e](https://github.com/xeek-dev/squishmark/commit/57fe50e1d858540c4af052cfdd5097817dca83a9))
* **dx:** make start-dev.py work on Windows ([#58](https://github.com/xeek-dev/squishmark/issues/58)) ([9b285ac](https://github.com/xeek-dev/squishmark/commit/9b285ac010e0de8d8d577847e844fc85aea857c7)), closes [#57](https://github.com/xeek-dev/squishmark/issues/57)
* **engine:** allow extra fields in ThemeConfig for theme extensibility ([#38](https://github.com/xeek-dev/squishmark/issues/38)) ([d4568b8](https://github.com/xeek-dev/squishmark/commit/d4568b83af420e869d78baf6caabe02205a99117)), closes [#37](https://github.com/xeek-dev/squishmark/issues/37)
* **engine:** serve dynamic pygments CSS when style is overridden ([#43](https://github.com/xeek-dev/squishmark/issues/43)) ([f5f2e37](https://github.com/xeek-dev/squishmark/commit/f5f2e374e6114541935df69c186ea10edbd9e511))
* **engine:** wire notes into post and page rendering ([#59](https://github.com/xeek-dev/squishmark/issues/59)) ([#72](https://github.com/xeek-dev/squishmark/issues/72)) ([cc56043](https://github.com/xeek-dev/squishmark/commit/cc560436a429a63ce21035fa662579206d93673c))
* **markdown:** change heading anchor symbol from ¶ to # ([#41](https://github.com/xeek-dev/squishmark/issues/41)) ([b8522ee](https://github.com/xeek-dev/squishmark/commit/b8522ee5846de579bf3315b1afb594efc57aed8d))
* **markdown:** clean heading links — wrap text in anchor instead of # marker ([#70](https://github.com/xeek-dev/squishmark/issues/70)) ([a098986](https://github.com/xeek-dev/squishmark/commit/a0989868fe2b502dc7cf8f877b53f4009b7ac7ca))
* **posts:** filter draft posts from public view ([#42](https://github.com/xeek-dev/squishmark/issues/42)) ([5cf87f5](https://github.com/xeek-dev/squishmark/commit/5cf87f57a2f981e35f5a5ac96b2b33c6dfdf2ef5))
* **theme:** wire dynamic pygments CSS into theme templates ([#44](https://github.com/xeek-dev/squishmark/issues/44)) ([028fcc8](https://github.com/xeek-dev/squishmark/commit/028fcc8bbb838d7607a0b76703c3df61c0c6437a)), closes [#33](https://github.com/xeek-dev/squishmark/issues/33)
* use correct 'build-target' property in fly.toml ([#19](https://github.com/xeek-dev/squishmark/issues/19)) ([3b7c588](https://github.com/xeek-dev/squishmark/commit/3b7c588d75e065f934cfafaccf80ac5e16d55315)), closes [#18](https://github.com/xeek-dev/squishmark/issues/18)


### Code Refactoring

* **blue-tech:** consistent accent styling for nav and hero titles ([#26](https://github.com/xeek-dev/squishmark/issues/26)) ([2dee20c](https://github.com/xeek-dev/squishmark/commit/2dee20c9ea0d08d88fc87373a7d0975cba017071))
* split theme.py into focused subpackage ([#17](https://github.com/xeek-dev/squishmark/issues/17)) ([87214a2](https://github.com/xeek-dev/squishmark/commit/87214a2e00b26a0a898f1f388851b0f5c427675b))


### Documentation

* add badges to README ([981f41f](https://github.com/xeek-dev/squishmark/commit/981f41f2c2727bc6b11be07cab0e9bb0687659e7))
* **github:** create GitHub skill with gh CLI patterns ([#39](https://github.com/xeek-dev/squishmark/issues/39)) ([a291051](https://github.com/xeek-dev/squishmark/commit/a29105118f07e48e4272ef7095414e1e1031deba))
* **github:** resolve Copilot threads before merging ([#81](https://github.com/xeek-dev/squishmark/issues/81)) ([b64c381](https://github.com/xeek-dev/squishmark/commit/b64c38159b608cc22d0f2fc39c7239b77206f9be))
* **themes:** create theme creator skill ([#40](https://github.com/xeek-dev/squishmark/issues/40)) ([1dbf467](https://github.com/xeek-dev/squishmark/commit/1dbf46708d7949581579ac71c2726abd25e9a583)), closes [#35](https://github.com/xeek-dev/squishmark/issues/35)


### Tests

* **routes:** add integration tests for core http endpoints ([#91](https://github.com/xeek-dev/squishmark/issues/91)) ([7f61002](https://github.com/xeek-dev/squishmark/commit/7f61002501dbddef5d1e47b163f481903d96bde0))


### Continuous Integration

* **commits:** allow any casing in pr title subject ([#99](https://github.com/xeek-dev/squishmark/issues/99)) ([1e77594](https://github.com/xeek-dev/squishmark/commit/1e77594dd1b29414967d045214bf6f639e9345eb))
* **release:** add release-please for automated versioning and changelog ([#88](https://github.com/xeek-dev/squishmark/issues/88)) ([39e802c](https://github.com/xeek-dev/squishmark/commit/39e802ccac9c2c425531bb8567cfbe3b175be791))


### Miscellaneous

* add copilot-instructions.md and update CLAUDE.md ([c97075e](https://github.com/xeek-dev/squishmark/commit/c97075e1546bbcedb79e40e81d7175298181da7b))
* **deps-dev:** Update ruff requirement ([#97](https://github.com/xeek-dev/squishmark/issues/97)) ([98886ac](https://github.com/xeek-dev/squishmark/commit/98886ac3f15c29d82c35035331243eeb512bf36a))
* **deps:** add dependabot version updates for pip, github-actions, and docker ([#90](https://github.com/xeek-dev/squishmark/issues/90)) ([77573cb](https://github.com/xeek-dev/squishmark/commit/77573cb2522a5008ca9f86d429d7a9c787db68e4))
* **deps:** Bump actions/checkout from 4 to 6 ([#95](https://github.com/xeek-dev/squishmark/issues/95)) ([5166f5a](https://github.com/xeek-dev/squishmark/commit/5166f5ae28e416dffa56adb4ca79b46f17a39059))
* **deps:** Bump actions/setup-python from 5 to 6 ([#96](https://github.com/xeek-dev/squishmark/issues/96)) ([6e62ef5](https://github.com/xeek-dev/squishmark/commit/6e62ef5e7a20fccdb837434da045d3da1c5d91ae))
* **deps:** Bump amannn/action-semantic-pull-request from 5 to 6 ([#94](https://github.com/xeek-dev/squishmark/issues/94)) ([306b42e](https://github.com/xeek-dev/squishmark/commit/306b42e8d5129ed41488a25bbfee92a82984d004))
* **deps:** Bump hadolint/hadolint-action ([#93](https://github.com/xeek-dev/squishmark/issues/93)) ([be1e968](https://github.com/xeek-dev/squishmark/commit/be1e96817873688cee3a9ff4d0204efe0266922c))
* **dev:** add --install and --with-content flags to setup-worktree.py ([#55](https://github.com/xeek-dev/squishmark/issues/55)) ([4ba9d45](https://github.com/xeek-dev/squishmark/commit/4ba9d453fccc39f74d9ac33e08249800de17057f))
* **dev:** add developer scripts for checks, worktrees, and server management ([#47](https://github.com/xeek-dev/squishmark/issues/47)) ([cbb2fa5](https://github.com/xeek-dev/squishmark/commit/cbb2fa5dca2165a3da43c45fede10488bbd0a67a))
* **dx:** clean up Claude Code permission settings ([#65](https://github.com/xeek-dev/squishmark/issues/65)) ([69c1dac](https://github.com/xeek-dev/squishmark/commit/69c1dac541d599757e927985e6241ec0ba4552f2))
* **dx:** replace playwright MCP skill with playwright-cli skill ([#56](https://github.com/xeek-dev/squishmark/issues/56)) ([0a0da53](https://github.com/xeek-dev/squishmark/commit/0a0da53c93328276f8243286869853947913b543))
* **dx:** slim CLAUDE.md and restructure skills ([#73](https://github.com/xeek-dev/squishmark/issues/73)) ([#74](https://github.com/xeek-dev/squishmark/issues/74)) ([3dfa358](https://github.com/xeek-dev/squishmark/commit/3dfa358993b89ee9b8d67ae5dbfd3adff023197c))
* **dx:** tighten github skill — issue creation flow + Copilot review docs ([#80](https://github.com/xeek-dev/squishmark/issues/80)) ([4545f16](https://github.com/xeek-dev/squishmark/commit/4545f1688119e28844580f8891e9cd48c7c8b7fa))
* implement complete blogging engine ([#1](https://github.com/xeek-dev/squishmark/issues/1)) ([a7cbb86](https://github.com/xeek-dev/squishmark/commit/a7cbb86318238de5b053e221d5e9ae715139df1c))
* improve Claude Code configuration ([#21](https://github.com/xeek-dev/squishmark/issues/21)) ([40c43f4](https://github.com/xeek-dev/squishmark/commit/40c43f43587e9a39bf68a8a364c5c7866c86c3e1))
