# hello-quint

TLA+ 系の仕様言語 **Quint** で「テストケースではなくルール（不変条件）を書く」を最小構成で体験するリポジトリ。

題材はチケット販売。確認画面で在庫を見て、確定ボタンで在庫を1枚減らす。AI が書いた実装は確定時に在庫を再確認しないので、確認と確定の間に他人が買うと在庫が負になる（売り越し）。

`ticket.qnt`（バグあり）と `ticket_fixed.qnt`（修正版）を並べ、`noOversell` という1本のルールだけでバグを捕まえる。

**このリポジトリの狙いは2つ**。Python の `pytest` と体験を比べること、そして [hello-lean-proof](https://github.com/nishimotz/hello-lean-proof) の続きとして読めること。

## 元ネタ

- Zenn「【TLA+】AIにテストケースを書かせるな。ルールを書け」（karamage, 2026-11）
  https://zenn.dev/karamage/articles/73027ee36796dc
- Quint 公式: https://quint.sh/
- Reliable Software in the LLM Era: https://quint.sh/posts/llm_era
- Model-based Testing: https://quint.sh/docs/model-based-testing

## 動かす

```bash
npm install

# 1. バグあり: ルール違反の手順が出る
npx quint run ticket.qnt --invariant=noOversell

# 2. 修正版: ランダム探索では見つからない
npx quint run ticket_fixed.qnt --invariant=noOversell

# 3. 修正版: 到達可能な状態を全部調べる
npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc
```

`quint verify` だけは新しい JVM を要求する（Apalache の都合）。環境構築で詰まったら [docs/macos-intel.md](docs/macos-intel.md) を見る。Linux / Apple Silicon では不要な可能性が高い。

---

## pytest との体験比較

**Quint は「テストを書いて走らせる」の形を保ったまま、書くものをケースからルールに置き換える。** ここが Python 利用者にとっての入口になる。

### 同じバグを pytest で捕まえようとすると

`TicketService` は記事の `ticket-service.ts` を Python に読み替えた想定コード。

```python
def test_sequential_purchase():
    svc = TicketService(stock=2)
    svc.check("alice")
    svc.purchase("alice")
    assert svc.stock == 1

def test_sold_out():
    svc = TicketService(stock=0)
    svc.check("alice")
    assert svc.phase["alice"] == "SoldOut"
```

この2本は通る。しかし**割り込みのバグは出てこない**。テストケースを書いた人が「確認と確定の間に他人が買う」場面を思いついていないから。AI に書かせても同じで、実装した AI が想定していない場面はテストにも現れない（自作自演の満点）。

### Quint ではケースを書かない

```
val noOversell = sold <= INITIAL_STOCK
```

これがルール。ケースは1つも書いていない。誰がどの順番で操作するかは `quint run` が勝手に決める。

```
$ npx quint run ticket.qnt --invariant=noOversell

[State 3] { phase: Map("alice" -> Checked, "bob" -> Checked, "carol" -> Checked), sold: 0, stock: 2 }
[State 4] { phase: Map("alice" -> Bought,  "bob" -> Checked, "carol" -> Checked), sold: 1, stock: 1 }
[State 5] { phase: Map("alice" -> Bought,  "bob" -> Bought,  "carol" -> Checked), sold: 2, stock: 0 }
[State 6] { phase: Map("alice" -> Bought,  "bob" -> Bought,  "carol" -> Bought),  sold: 3, stock: -1 }

[violation] Found an issue (19ms at 1000 traces/second).
error: Invariant violated
```

**3人が確認してから3人が確定した**。在庫は2枚しかない。State 6 で `stock: -1`、`sold: 3`。

`pytest` が落ちたときと同じ体験。**違うのは、落ちた原因が「書かなかったケース」ではなく「破られたルール」として示されること**。手順まで出るので、どこで破れたかがそのまま読める。

### 対応表

| | pytest | Quint |
|---|---|---|
| 人間が書くもの | テストケース（入力と期待値） | ルール（不変条件） |
| ケースの生成 | 人間 | 機械（ランダム or 全探索） |
| 失敗したとき | テスト名と assert の場所 | 破ったルールと手順トレース |
| 通ったときの意味 | 書いたケースの範囲で正しい | `run` は確率的、`verify` は全状態 |
| 増やすコスト | ケース1本ずつ | ルール1行（対象は自動で広がる） |

「全部試した」と言えるのは `quint verify --backend=tlc` のほうだけ。`quint run` はランダムなので pytest より広いが保証はない。この区別は教材で明示する。

---

## hello-lean-proof との接続

[hello-lean-proof](https://github.com/nishimotz/hello-lean-proof) は Lean 4 で「証明＝探索ゲーム」を体験する教材。同じ題材（チケット販売の売り越し）を Lean で書くと、Quint との差がはっきり出る。

### 同じ `purchase` を並べる

Quint:

```
action purchase(u: str): bool = all {
  phase.get(u) == Checked,
  stock' = stock - 1,
  sold' = sold + 1,
  phase' = phase.set(u, Bought),
}
```

Lean 4:

```lean
| purchase : ∀ (a b : Int) (c : Nat), 1 ≤ c → 0 < a →
    StepFixed ⟨a, b, c⟩ ⟨a - 1, b + 1, c - 1⟩
```

Quint は「状態をこう書き換える」と素直に読める。Lean は遷移を関係として書き、証明側でその関係を帰納法に載せる。

### 差が出るのは証明するところ

Lean で `noOversell`（`sold ≤ 2`）をそのまま帰納法に載せると詰まる。1手進めるのに在庫との関係が要るから。だから不変条件を強化する。

```lean
def Inv (s : St) : Prop := 0 ≤ s.stock ∧ s.sold + s.stock = 2
```

これで初めて `fixed_no_oversell` が通る。

> **Quint はルールをそのまま渡せば機械が全状態を調べる。Lean はルールを帰納的な形に書き直す仕事が人間に残る。その代わり、人数も在庫数も固定せずに証明が通る。**

これが「ルールを書け」の Lean 側の読み替え。記事の主張を否定せずに一段深くする形になる。

### どこから読むか

| 順番 | リポジトリ | 得られるもの |
|---|---|---|
| 1 | ここ（hello-quint） | ルールを書けばケースを書かなくていい、という体験。`quint run` が pytest の代わり |
| 2 | hello-lean-proof | 同じ題材を、状態数を数えずに一般化する。`Inv` 強化の必然性 |
| 3 | ここに戻る | `quint verify` の「29状態を全部見た」と Lean の「任意の人数で成り立つ」の違いを言語化 |

### 正直に書く弱点

記事の山場の一つ「モデルベーステストで1000トレース生成 → AI の実装が578本で不一致」は、**Lean 単体では閉じない**。実装（TypeScript など）とモデルをつなぐ層が要る。Quint は `--mbt` でこの層を自前で持っている。Lean で同じことをやるなら抽出か外部突き合わせになる。ここは Lean 連載の弱点として明示する。

---

## ファイルの見方

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

## 実測値

2026-11-22、クリーンクローンから `npm install` して実行:

| コマンド | 結果 |
|---|---|
| `quint run ticket.qnt --invariant=noOversell` | `[violation] Found an issue (19ms at 1000 traces/second)`、`sold: 3` |
| `quint run ticket_fixed.qnt --invariant=noOversell` | `[ok] No violation found (64ms)` |
| `quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc` | `55 states generated, 29 distinct states found, 0 states left on queue`、`[ok] (606ms)` |

絶対時間は環境依存。初回は Apalache のキャッシュ生成で秒単位になる。詳細は [docs/macos-intel.md](docs/macos-intel.md)。

## ライセンス

MIT
