# Windows（PowerShell）でのセットアップ・検証記録

このページは Windows の **PowerShell** から始める人向けのセットアップ手順と実機検証記録。教材の本筋ではない。

> **検証状況**: Windows 11 Pro x64（`10.0.26200`）、PowerShell `7.6.10` および Windows PowerShell `5.1.26100.9818`、Node `v26.7.0` / npm `11.19.0`、quint `0.33.1`、Eclipse Temurin JRE `21.0.13.1`、`uv 0.13.7`（Python `3.15.2` / pytest `9.2.0`）で全コマンドの動作を確認済み（2026-11-22）。
> Windows ARM 実機、`winget` 以外の Java 導入経路、WSL 内での実行は未確認。

---

## 1. 必要なもの

- **Node.js 18 以上** — `quint run`（ランダム探索）だけなら Node.js 単体で動く
- **Java 21 以上** — `quint verify`（全状態探索）を使う場合のみ必要。**Java 11 や Java 17 では動かない**（後述）
- 任意: **`uv`** — [compare-pytest.md](compare-pytest.md) の Python / pytest 比較を動かす場合

---

## 2. 動かす（基本手順）

```powershell
git clone https://github.com/nishimotz/hello-quint.git
cd hello-quint
npm install

# 1. バグあり: ルール違反の手順が出る
npx quint run ticket.qnt --invariant=noOversell

# 2. 修正版: ランダム探索では見つからない
npx quint run ticket_fixed.qnt --invariant=noOversell

# 3. 修正版: 到達可能な状態を全部調べる（要 Java 21+）
npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc
```

`package.json` に定義されている `npm run buggy` / `npm run fixed` / `npm run verify` も同様に動く。

初回実行時は `%USERPROFILE%\.quint\` 配下に依存バイナリが自動取得される。

- 初回 `quint run`: Rust evaluator `v0.7.1`（`%USERPROFILE%\.quint\rust-evaluator-v0.7.1\quint_evaluator.exe`）
- 初回 `quint verify`: Apalache `0.62.4`（`%USERPROFILE%\.quint\apalache-dist-0.62.4\`。回線状況により数十秒〜2分程度かかる）

---

## 3. `quint verify` には Java 21 以上が要る

`quint verify --backend=tlc` は内部で Apalache `0.62.4` を経由して TLA+ に変換する。Apalache `0.62.4` の `at.forsyte.apalache.tla.Tool` は **class file version 65.0（Java 21）** でコンパイルされているため、Java 17（上限 `61.0`）や Java 11（上限 `55.0`）では起動時に落ちる。

```
java.lang.UnsupportedClassVersionError: at/forsyte/apalache/tla/Tool has been compiled by a more recent version of the Java Runtime (class file version 65.0), this version of the Java Runtime only recognizes class file versions up to 61.0
```

Unix 版のランチャー（`apalache-mc`）と異なり、Windows 版の `apalache-mc.bat` は `-XX:G1PeriodicGCInterval=600000` を渡さないため、Java 11 でも VM オプションエラーではなく同じ `UnsupportedClassVersionError`（`65.0` vs `55.0`）になる。

### 導入（`winget`）

```powershell
winget install --id EclipseAdoptium.Temurin.21.JRE --exact
```

`javac` など開発ツールも必要なら `EclipseAdoptium.Temurin.21.JDK` を使う。

- インストーラーは WiX（`.msi`）のため実行時に UAC の許可ダイアログが出る
- マシン環境変数の `JAVA_HOME` と `PATH` 先頭が自動で更新されるが、**開いている PowerShell には即座に反映されない**ため、インストール後に **PowerShell を開き直してから** `java -version` を確認すること

### 注意: Windows では `JAVA_HOME` だけでは切り替わらない

`apalache-mc.bat` も Quint の TLC ランナー（`tlc.js`）も、コマンド名 `java` を **`PATH` 経由で直接呼び出す**（`JAVA_HOME` を見ない）。

実機確認でも、`$env:JAVA_HOME` だけ JRE 21 に向けて `PATH` 先頭が JRE 17 のままだと、`where.exe java` が JRE 17 を先に拾って `UnsupportedClassVersionError` で失敗した。古い Java を既定に残したまま一時的に切り替える場合は、`PATH` の先頭に Java 21 の `bin` を置く（ディレクトリ名のバージョン部分は導入環境に合わせて読み替える）。

```powershell
$env:PATH = "C:\Program Files\Eclipse Adoptium\jre-21.0.13.10002-hotspot\bin;$env:PATH"
npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc
```

---

## 4. Windows で詰まりやすい点・既知の挙動

| 症状 | 原因と対処 |
|---|---|
| `UnsupportedClassVersionError`（`class file version 65.0`） | Java 21 未満で実行している。Java 21 以上を入れ、PowerShell を開き直すか `PATH` 先頭に通す |
| `JAVA_HOME` を変えたのに古い Java が使われる | `apalache-mc.bat` / `tlc.js` は `PATH` 上の `java` を呼ぶ。`where.exe java` で先頭を確認し、`PATH` の順序を変える |
| `npm.ps1` / `npx.ps1` が実行ポリシーで止まる | `Set-ExecutionPolicy -Scope Process Bypass` を実行する（そのウィンドウのみ有効） |
| `npm install` で `protobufjs@7.6.6` の `allowScripts` 警告が出る | npm 11 のスクリプト実行ポリシーによる情報メッセージ。`package-lock.json` に変更は入らず動作にも影響しない |
| `makeExtensionsImmutable`（protobuf）や `-XX:+UseParallelGC` の警告が出る | Apalache / TLC の既知の警告で、検証結果に影響しない（[macos-intel.md](macos-intel.md) と同様） |
| Java の警告・エラーの先頭（日時や「エラー」「警告」）が文字化けする | 日本語 Windows 環境で Java が CP932 で出力した文字列と UTF-8 ターミナルの差異によるもの。英語の本文と検証結果は読める |
| `--backend=tlc` を外すと `error: reached a deadlock` で失敗する | 既定の Apalache（SMT）バックエンドではデッドロック検査が有効なため、3人全員が `Bought`/`SoldOut` に達して次の遷移が無くなると違反扱いになる。`--backend=tlc` は内部で `-deadlock` を渡すため通る。README 通り `--backend=tlc` を付けて実行する |
| `_apalache-out/` が残る | `quint verify` が生成する出力ディレクトリ（`.gitignore` 済み）。不要なら `Remove-Item -Recurse -Force _apalache-out` で削除できる |

---

## 5. 実測値（Windows x64 / 2026-11-22）

検証環境: Windows 11 Pro `10.0.26200` x64 / PowerShell `7.6.10` / Node `v26.7.0` / npm `11.19.0` / quint `0.33.1` / Temurin JRE `21.0.13.1`。

| コマンド | 結果 |
|---|---|
| `npx quint run ticket.qnt --invariant=noOversell` | `[violation] Found an issue`、`sold: 3`、`stock: -1`（初回 `3010ms`・Rust evaluator 取得込み / 2回目以降 `20〜24ms`） |
| `npx quint run ticket.qnt --invariant=noOversell --seed=0x1d882ec7345faa98` | `[violation] Found an issue (20ms)`、State 3〜6 が [README.md](../README.md) の出力例と完全一致 |
| `npx quint run ticket_fixed.qnt --invariant=noOversell` | `[ok] No violation found (56ms)`（Windows PowerShell 5.1 でも `48ms` で成功） |
| `npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc` | `55 states generated, 29 distinct states found, 0 states left on queue`、`[ok] (1086〜1095ms)`（コマンド全体 `6.8〜11.4s`、PS 5.1 でも `1082ms` で成功。初回 Apalache 取得は別途約 `116s`） |
| `npx quint verify ticket.qnt --invariant=noOversell --backend=tlc` | `55 states generated, 30 distinct states found`、`[violation] (1119ms)`、`stock = -1, sold = 3` |
| `npm run buggy` / `npm run fixed` / `npm run verify` | すべて上記と同一の終了コード（`1` / `0` / `0`）・結果で動作確認 |
| `uv run --with pytest pytest -q test_ticket_service.py`（`docs/compare-pytest/`） | `3 passed in 0.01s`（`Python 3.15.2` / `pytest 9.2.0`） |
| `uv run --with pytest pytest -q test_interleaved.py`（`docs/compare-pytest/`） | `1 failed in 0.05s`（`assert -1 >= 0`、想定通り） |

---

## 6. 未確認事項

- 実機 Windows ARM での動作（Rust evaluator の配信バイナリ含む）
- `winget` 以外の Java 導入経路（Scoop、ポータブル ZIP など）
- WSL 内での実行（Linux と同じ手順になる見込みだが本リポジトリでの実測は未実施）
