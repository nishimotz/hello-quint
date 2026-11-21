# macOS 固有の事情（Intel Mac で検証した記録）

検証環境: macOS 15.8.3 x64（Intel）、Node 24.22.3、quint 0.33.1、Homebrew は `/usr/local`。

このファイルは環境構築で詰まった点だけを集めたもの。教材の本筋ではない。Linux / Apple Silicon では該当しない可能性が高い。

## 1. `quint verify --backend=tlc` には新しい JVM が要る

`--backend=tlc` は内部で Apalache 経由の TLA+ 変換を行う。Apalache 0.62.4 が `G1PeriodicGCInterval=600000` を JVM に渡すため、既定の `java` が 11 だと落ちる。

```
Unrecognized VM option 'G1PeriodicGCInterval=600000'
Error: Could not create the Java Virtual Machine.
Error: A fatal exception has occurred. Program will exit.
```

`G1PeriodicGCInterval` は JDK 12 以降のオプション。JDK 11 では認識されない。

### 回避

```bash
export JAVA_HOME=/usr/local/opt/openjdk
npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc
```

Homebrew の `openjdk` は keg-only なので `java` の PATH は変わらない。`JAVA_HOME` を明示するか、`$(brew --prefix openjdk)/bin` を PATH の前に置く。

### 入っている JVM の確認

```bash
/usr/libexec/java_home -V
```

このマシンでは 4 本入っていた。

```
11.0.1  (x86_64) "Oracle Corporation" - "OpenJDK 11.0.1"
1.8.0_504 (x86_64) "Eclipse Temurin" - "Eclipse Temurin 8"
1.8.0_361 (x86_64) "Oracle Corporation" - "Java SE 8"
1.8.0_192 (x86_64) "Oracle Corporation" - "Java SE 8"
```

`/usr/libexec/java_home` が返す既定は 11.0.1 だった。`openjdk`（Homebrew 26）は `/Library/Java/JavaVirtualMachines` に入らないので、この一覧には出てこない。

## 2. Homebrew のプレフィックス

Intel Mac は `/usr/local`、Apple Silicon は `/opt/homebrew`。

```bash
brew --prefix          # /usr/local （このマシン）
ls $(brew --prefix)/opt | grep -i openjdk
```

README の手順を他環境に持ち出すときは `$(brew --prefix openjdk)` に置き換えるのが安全。

## 3. TLC 起動時の protobuf 警告

`quint verify` の出力に次の警告が1行出る。

```
As of 2022/09/29 (release 21.7) makeExtensionsImmutable should not be called from protobuf gencode.
...
```

Apalache 同梱の protobuf 生成コードが古いことによる警告。探索結果には影響しない。無視してよい。

## 4. `quint run` の速度は環境依存

同じ `ticket.qnt` でも実行時間は大きく変わる。

| 環境 | `quint run ticket.qnt` |
|---|---|
| このマシン（Intel, Node 24.22.3, quint 0.33.1, 初回） | 1924ms（12 traces/second） |
| このマシン（クリーンクローン後） | 19ms（1000 traces/second） |
| 元記事（環境不明） | 12ms |

初回は Node のモジュール解決と Apalache のキャッシュ生成で遅い。2回目以降は桁が変わる。**教材に書くべきは絶対時間ではなく「ミリ秒〜秒で反例が出る」という性質**。

## 5. `_apalache-out/` が生成される

`quint verify` を実行すると、カレントディレクトリに `_apalache-out/` ができる。中身は TLA+ 変換結果とキャッシュ。リポジトリには含めない（`.gitignore` 済み）。

```bash
rm -rf _apalache-out
```
