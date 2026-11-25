# macOS（Apple Silicon）でのセットアップ記録

このページは Apple Silicon の Mac で動かす人向けのセットアップ手順と実機検証記録。教材の本筋ではない。`docs/macos-intel.md` は Intel Mac 前提で `brew --prefix` を `/usr/local` と書いているため、Apple Silicon ではパスが違う（`/opt/homebrew`）。

> **検証状況**: macOS 27.2.1（arm64）、Node `v25.1.0` / npm `11.19.0`、quint `0.33.1`、Homebrew `openjdk` 26.0.2、`uv 0.13.6`（Python `3.15.2` / pytest `9.2.0`）で全コマンドの動作を確認済み（2026-11-25）。

---

## 1. 必要なもの

- **Node.js 18 以上** — `quint run`（ランダム探索）だけなら Node.js 単体で動く
- **Java 21 以上** — `quint verify`（全状態探索）を使う場合のみ必要。**Java 11 や Java 17 では動かない**（理由は [macos-intel.md](macos-intel.md) の「1. `quint verify --backend=tlc` には Java 21 以上が要る」）
- 任意: **`uv`** — [compare-pytest.md](compare-pytest.md) の Python / pytest 比較を動かす場合

`java -version` が `Unable to locate a Java Runtime` になるなら Java が入っていない。Homebrew なら:

```bash
brew install openjdk
```

`openjdk` は keg-only なのでインストールしても `java` の PATH は変わらない。`JAVA_HOME` を明示する必要がある。

---

## 2. `JAVA_HOME` の設定

`openjdk` は keg-only なので、`JAVA_HOME` を明示するか `$(brew --prefix openjdk)/bin` を PATH の前に通す必要がある。Apple Silicon では `$(brew --prefix openjdk)` が `/opt/homebrew/opt/openjdk`。

`~/.zshrc`（対話シェル）に置いた例。既に `JAVA_HOME` が入っていれば上書きしない:

```bash
if [ -z "$JAVA_HOME" ] && [ -x /opt/homebrew/opt/openjdk/bin/java ]; then
  export JAVA_HOME=/opt/homebrew/opt/openjdk
fi
export PATH="$JAVA_HOME/bin:$PATH"
```

VSCode のタスクや `zsh -lc`（ログインシェル）からも使いたい場合は、同じガードを `~/.zprofile` の `brew shellenv` より後ろにも置く。こちらは PATH もガードの中に入れている（`.zprofile` 側は `JAVA_HOME` が空なら PATH を触らない）。

```bash
if [ -z "$JAVA_HOME" ] && [ -x /opt/homebrew/opt/openjdk/bin/java ]; then
  export JAVA_HOME=/opt/homebrew/opt/openjdk
  export PATH="$JAVA_HOME/bin:$PATH"
fi
```

`JAVA_HOME` が既に入っていれば二重には足さないので、両方に置いても衝突しない。

`JAVA_HOME` は全プロジェクトに効く。Android Studio など特定の JDK を要求する作業と同居しているなら、リポジトリごとに `export JAVA_HOME=...` するだけにしておくほうが安全。

確認:

```bash
zsh -ic 'echo $JAVA_HOME; java -version'
zsh -lc 'echo $JAVA_HOME; java -version'
```

次のように返れば準備完了。

```
/opt/homebrew/opt/openjdk
openjdk version "26.0.2" 2026-07-21
```

`/usr/bin/java` のスタブが先に居ても `JAVA_HOME` があれば quint はそちらを使う。`quint verify` が `Unable to locate a Java Runtime` を出すなら `JAVA_HOME` が空のまま。

---

## 3. 動かす

```bash
npm install

npm run buggy    # バグあり: 反例が出る
npm run fixed    # 修正版: ランダム探索では見つからない
npm run verify   # 修正版: 全状態探索（要 Java 21+）
```

`npm run verify` が

```
55 states generated, 29 distinct states found, 0 states left on queue.
[ok] No violation found (317ms).
```

で終われば全探索が動いている。失敗するときは `JAVA_HOME` が空のまま（`Unable to locate a Java Runtime`）か、JDK が 21 未満。

初回実行時は `~/.quint/` 配下に依存バイナリが自動取得される。

- 初回 `quint run`: Rust evaluator `v0.7.1`
- 初回 `quint verify`: Apalache `0.62.4`（回線状況により数十秒〜2分程度かかる）

---

## 4. npm の install script 警告

`npm install` の最後に次の警告が出る。

```
npm warn install-scripts 1 package has install scripts not yet covered by allowScripts:
npm warn install-scripts   protobufjs@7.6.6 (postinstall: node scripts/postinstall)
```

protobufjs の postinstall は、依存側の `package.json` が `protobufjs` を `~` 付き以外の版指定で持っていないかを見て警告を出すだけのスクリプトで、何も生成しない。quint の `run` / `verify` はこのまま動く。

---

## 5. `_apalache-out/` が生成される

`npm run verify` を実行すると、カレントディレクトリに `_apalache-out/` ができる。中身は TLA+ 変換結果とキャッシュ。リポジトリには含めない（`.gitignore` 済み）。

```bash
rm -rf _apalache-out
```
