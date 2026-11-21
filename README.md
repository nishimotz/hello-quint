# hello-quint

TLA+ 系の仕様言語 **Quint** で「テストケースではなくルール（不変条件）を書く」を最小構成で体験するリポジトリ。

題材はチケット販売。確認画面で在庫を見て、確定ボタンで在庫を1枚減らす。AI が書いた実装は確定時に在庫を再確認しないので、確認と確定の間に他人が買うと在庫が負になる（売り越し）。

このリポジトリは `ticket.qnt`（バグあり）と `ticket_fixed.qnt`（修正版）を並べ、`noOversell` という1本のルールだけでバグを捕まえる。

## 元ネタ

- Zenn「【TLA+】AIにテストケースを書かせるな。ルールを書け」（karamage, 2026-11）
  https://zenn.dev/karamage/articles/73027ee36796dc
- Quint 公式: https://quint.sh/
- Reliable Software in the LLM Era: https://quint.sh/posts/llm_era
- Model-based Testing: https://quint.sh/docs/model-based-testing

## 動かす

```bash
npm install
npx quint --version   # 0.33.1

# 1. バグあり: ルール違反の手順が出る
npx quint run ticket.qnt --invariant=noOversell

# 2. 修正版: ランダム探索では見つからない
npx quint run ticket_fixed.qnt --invariant=noOversell

# 3. 修正版: 到達可能な状態を全部調べる
npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc
```

### 実測値（2026-11-22, macOS 15.8.3 x64, Node 24.22.3）

| コマンド | 結果 |
|---|---|
| `quint run ticket.qnt --invariant=noOversell` | `[violation] Found an issue (1924ms at 12 traces/second)`。State 0〜6 で `stock: -1, sold: 3` |
| `quint run ticket_fixed.qnt --invariant=noOversell` | `[ok] No violation found (74ms at 135135 traces/second)` |
| `quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc` | `55 states generated, 29 distinct states found, 0 states left on queue`、深さ 7、`[ok] (606ms)` |

`quint run` の 1924ms は元記事の「12ms」と桁が違う。記事の環境依存なので、ここでは実測をそのまま置く。重要なのは**ミリ秒で反例が出る**という性質のほう。

## `quint verify` には新しい JVM が要る

`--backend=tlc` は内部で Apalache 経由の TLA+ 変換を行う。既定の `java` が 11 だと落ちる:

```
Unrecognized VM option 'G1PeriodicGCInterval=600000'
Error: Could not create the Java Virtual Machine.
```

Apalache 0.62.4 が新しい JVM のオプションを渡すため。手元では Homebrew の `openjdk`（26）を指すと通った:

```bash
export JAVA_HOME=/usr/local/opt/openjdk
npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc
```

Intel Mac の Homebrew は `/usr/local`、Apple Silicon は `/opt/homebrew`。`/usr/libexec/java_home -V` で入っている一覧が見える。

## 何を見るファイルか

`ticket.qnt`:

- `pure val USERS = Set("alice", "bob", "carol")` — 3人
- `pure val INITIAL_STOCK = 2` — 在庫2枚
- `type Phase = Idle | Checked | Bought | SoldOut` — 確認画面の状態
- `action purchase(u)` — **`phase.get(u) == Checked` だけで在庫を見ない**。ここがバグ
- `val noOversell = sold <= INITIAL_STOCK` — 守るべきルール。テストケースは1つも書いていない

`ticket_fixed.qnt` は `purchase` に在庫の再確認を足しただけ:

```quint
action purchase(u: str): bool = all {
  phase.get(u) == Checked,
  if (stock > 0) all {
    stock' = stock - 1,
    sold' = sold + 1,
    phase' = phase.set(u, Bought),
  } else all {
    stock' = stock,
    sold' = sold,
    phase' = phase.set(u, SoldOut),
  },
}
```

## Lean 4 版との対比

同じ題材を Lean 4 で書いたもの: https://github.com/nishimotz/hello-lean-proof

| | Quint / TLA+ | Lean 4 |
|---|---|---|
| 人間が書くもの | ルール（そのまま渡せる） | ルール＋**帰納的な不変条件への強化** |
| 探索 | `quint run`（ランダム）／`quint verify`（全状態） | 帰納法（状態数を数えない） |
| 反例 | 手順を自動表示 | 自分で構成する |
| 強さ | 具体的なモデルに閉じる | 人数・在庫数を固定しなくても証明が通る |

Lean 側で `noOversell`（`sold ≤ 2`）を単独で帰納法に載せると詰まる。`0 ≤ stock ∧ sold + stock = 2` に強化して初めて通る。**「ルールを書く」は Lean では「帰納的な不変条件を書く」に読み替えが要る**、というのがこの2つを並べたときの差分。

## ライセンス

MIT
