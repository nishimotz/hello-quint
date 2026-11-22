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
#    注意: Java 21 以上が必要 → docs/macos-intel.md / docs/windows.md
npx quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc
```

`quint verify` だけは Java 21 以上を要求する（Apalache 0.62.4 の都合）。環境構築で詰まったら [docs/macos-intel.md](docs/macos-intel.md) または [docs/windows.md](docs/windows.md)（Windows x64 で実機検証済み）を見る。Linux / Apple Silicon でも Java 21 未満なら同様。

---

## pytest との体験比較

**Quint は「テストを書いて走らせる」の形を保ったまま、書くものをケースからルールに置き換える。** ここが Python 利用者にとっての入口になる。

### 同じバグを pytest で捕まえようとすると

`TicketService` は記事の `ticket-service.ts` を Python に読み替えた想定コード。[docs/compare-pytest.md](docs/compare-pytest.md) に動く版を置いた。

```python
# AI が書いたテスト（docs/compare-pytest/test_ticket_service.py より抜粋、名前は実物どおり）
def test_can_buy_when_in_stock():
    svc = TicketService(2, USERS)
    svc.check("alice")
    svc.purchase("alice")
    assert svc.stock == 1
    assert svc.sold == 1

def test_sold_out_when_no_stock():
    svc = TicketService(0, USERS)
    svc.check("alice")
    assert svc.phase["alice"] == "SoldOut"
```

実物はもう1本（`test_two_sequential_purchases`）あり、**3本とも通る**。しかし**割り込みのバグは出てこない**。テストケースを書いた人が「確認と確定の間に他人が買う」場面を思いついていないから。AI に書かせても同じで、実装した AI が想定していない場面はテストにも現れない（自作自演の満点）。

### Quint ではケースを書かない

```
val noOversell = sold <= INITIAL_STOCK
```

これがルール。ケースは1つも書いていない。誰がどの順番で操作するかは `quint run` が勝手に決める。

```
$ npx quint run ticket.qnt --invariant=noOversell --seed=0x1d882ec7345faa98

[State 3] { phase: Map("alice" -> Checked, "bob" -> Checked, "carol" -> Checked), sold: 0, stock: 2 }
[State 4] { phase: Map("alice" -> Bought,  "bob" -> Checked, "carol" -> Checked), sold: 1, stock: 1 }
[State 5] { phase: Map("alice" -> Bought,  "bob" -> Bought,  "carol" -> Checked), sold: 2, stock: 0 }
[State 6] { phase: Map("alice" -> Bought,  "bob" -> Bought,  "carol" -> Bought),  sold: 3, stock: -1 }

[violation] Found an issue (19ms at 53 traces/second).
error: Invariant violated
```

`quint run` はランダムなので、**手順は実行ごとに変わる**。上のトレースは `--seed` で固定した一例（seed を省略すると別の順序で同じ違反に着く）。最後の State 6（`sold: 3, stock: -1`）だけは、どの手順でも同じ。

この実行では alice と bob が先に確認して在庫1枚まで減り、carol が最後の1枚を買ったあとに bob が確定している。在庫は2枚しかない。**順序は問わない** — 確認と確定が交錯すれば `sold` は 2 を超え得る。

`pytest` が落ちたときと同じ体験。**違うのは、落ちた原因が「書かなかったケース」ではなく「破られたルール」として示されること**。手順まで出るので、どこで破れたかがそのまま読める。

### 対応表

| | pytest | Quint |
|---|---|---|
| 人間が書くもの | テストケース（入力と期待値） | ルール（不変条件） |
| ケースの生成 | 人間 | 機械（ランダム or 全探索） |
| 失敗したとき | テスト名と assert の場所 | 破ったルールと手順トレース |
| 通ったときの意味 | 書いたケースの範囲で正しい | `run` は確率的、`verify` はこのモデルの全状態で正しい |
| 増やすコスト | ケース1本ずつ | ルール1行（対象は自動で広がる） |

「全部試した」と言えるのは `quint verify --backend=tlc` のほうだけ。`quint run` はランダムなので pytest より広いが保証はない。

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
| 2 | hello-lean-proof [docs/formal-rules.md](https://github.com/nishimotz/hello-lean-proof/blob/main/docs/formal-rules.md) | 同じ題材の解説。`Inv` 強化の必然性と、`Exercises/07_state_invariant` の演習7問 |
| 3 | ここに戻る | `quint verify` の「29状態を全部見た」と Lean の「任意の人数で成り立つ」の違いを言語化 |

### 正直に書く弱点

記事の山場の一つ「モデルベーステストで1000トレース生成 → AI の実装が578本で不一致」は、**Lean 単体では閉じない**。実装（TypeScript など）とモデルをつなぐ層が要る。Quint は `--mbt` でこの層を自前で持っている。Lean で同じことをやるなら抽出か外部突き合わせになる。ここは Lean 連載の弱点として明示する。

---

## 最初に押さえる3つの記法

Quint を読むのに要るのはこの3つだけ。

- `all { ... }` — **中身が全部成り立つときだけ、この操作ができる**。条件と「次の状態での値」を並べる。条件が偽ならその手は起きない（盤面は変わらない）
- `any { ... }` — **どれか1つを選んで実行する**。「全部実行」ではない
- `nondet u = USERS.oneOf()` — **誰か1人を非決定的に選ぶ**。どの1人を選ぶかは機械が決める（だから人間が思いつかない順序も試される）

`stock'` の `'` は「次の時点の値」。`stock' = stock - 1` は「次の在庫は今の在庫から1引いたもの」。

**不変条件**（invariant）は「初期状態で成り立ち、どの操作をしても成り立ち続ける性質」。**モデル検査**（`quint verify`）は、到達可能な状態を機械的に全部たどって不変条件が破れないか調べる手法。

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

`else` 側で `SoldOut` に落とすのは設計判断。`purchase` の前提を `stock > 0` に狭めると、在庫切れのあとの確定操作が「起きない」ことになり、確認済みの人が残ったまま止まる。フェーズを `SoldOut` に進めて在庫も `sold` も変えないことで、「確定しようとしたが買えなかった」を状態として表現している。

## 実測値

2026-11-22、クリーンクローンから `npm install` して実行:

| コマンド | 結果 |
|---|---|
| `quint run ticket.qnt --invariant=noOversell` | `[violation] Found an issue (19ms at 1000 traces/second)`、`sold: 3` |
| `quint run ticket_fixed.qnt --invariant=noOversell` | `[ok] No violation found (64ms)` |
| `quint verify ticket_fixed.qnt --invariant=noOversell --backend=tlc` | `55 states generated, 29 distinct states found, 0 states left on queue`、`[ok] (606ms)` |

絶対時間は環境依存。初回は Rust evaluator / Apalache の取得とキャッシュ生成で秒〜分単位になる。詳細は [docs/macos-intel.md](docs/macos-intel.md)（macOS Intel）および [docs/windows.md](docs/windows.md)（Windows x64）。

## ライセンス

MIT
