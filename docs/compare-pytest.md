# pytest で同じバグを捕まえられるか（実測）

`ticket-service.ts` を Python に読み替え、pytest で同じ売り越しバグを捕まえようとするとどうなるかを実際に動かした記録。

実行環境: `uv run --with pytest` の Python 3.13.11 / pytest 9.2.0（macOS 15.8.3 x64）。

## 実装（バグあり）

`ticket_service.py`:

```python
class TicketService:
    def __init__(self, stock: int, users: list[str]):
        self.stock = stock
        self.sold = 0
        self.phase = {u: "Idle" for u in users}

    def check(self, user: str) -> None:
        self.phase[user] = "Checked" if self.stock > 0 else "SoldOut"

    def purchase(self, user: str) -> None:
        # 在庫は check() で確認済みなので、ここでは減らすだけでOK ← ここがバグ
        self.stock -= 1
        self.sold += 1
        self.phase[user] = "Bought"
```

## AI が書いたテスト3本

`test_ticket_service.py`:

```python
from ticket_service import TicketService

USERS = ["alice", "bob", "carol"]

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

def test_two_sequential_purchases():
    svc = TicketService(2, USERS)
    svc.check("alice"); svc.purchase("alice")
    svc.check("bob");   svc.purchase("bob")
    assert svc.stock == 0
    assert svc.sold == 2
```

結果:

```
$ uv run --with pytest pytest -q test_ticket_service.py
3 passed in 0.01s
```

**全部通る。** バグは残っている。

## なぜ通るか

3本とも「1人ずつ順番に買う」場面しか試していない。実装した AI が「順番に買う」ことしか想定していないので、テストにもその場面しか出てこない。テストオラクル問題。先生と生徒が同じ人物で、自作自演の満点になっている。

## 割り込みを自分で書くと捕まる

まず、**書いてはいけない例**。前提が崩れることをテストで観測できないと、バグは見えない。

```python
def test_interleaved_wrong():
    svc = TicketService(2, USERS)
    svc.check("bob")
    svc.check("carol")
    svc.purchase("alice_from_checked")   # 確認していない人が買う
    # ← ここで何も assert しない
```

この実装は前提を検査しないので、`purchase` は**例外も出さず stock を減らす**。`assert` が無いのでテストは通る。「前提が崩れる」と書いただけでは、実行しても何も起きない。**壊れたことを観測する仕掛け（不変条件の assert）を自分で置かないと、pytest は何も言わない** — これがこの節の要点。

正しくはこう:

```python
def test_interleaved_check_purchase():
    svc = TicketService(2, USERS)
    svc.check("alice"); svc.purchase("alice")   # 在庫1
    svc.check("bob")                             # bob は在庫1を見て Checked
    svc.check("carol"); svc.purchase("carol")   # carol が最後の1枚を買う
    svc.purchase("bob")                          # それでも bob は買える → 売り越し
    assert svc.stock >= 0   # ← ここで落ちる
```

**`assert svc.stock >= 0` が、Quint の `noOversell` を手で書いたもの**。ケース（操作手順）とルール（不変条件）を両方自分で書いている。Quint ではルールだけ書けば手順は機械が作る。

```
$ uv run --with pytest pytest -q test_interleaved.py
E       assert svc.stock >= 0
E       assert -1 >= 0
FAILED test_interleaved.py::test_interleaved_check_purchase
1 failed in 0.02s
```

**捕まる。ただし書いた人間が先に「確認と確定の間に他人が買う」を思いついている必要がある。** ここが pytest と Quint の分岐点。

## Quint との違い

| | pytest | Quint |
|---|---|---|
| 割り込みを思いつく必要 | ある | ない（機械が順序を生成する） |
| 同じバグを捕まえるのに必要な行数 | 6行（思いつけば） | 1行（`val noOversell = sold <= INITIAL_STOCK`） |
| 通ったときの意味 | 書いたケースの範囲で正しい | `verify` ならこのモデルの全状態で正しい |

pytest が悪いのではない。**ケースを書く方式である限り、書いた人の想像力が上限になる**という話。Quint はその上限を外す。

ただし `verify` の「全状態」は、`USERS` が3人・`INITIAL_STOCK` が2 という**この固定モデルの中での全状態**。4人に増やせば状態空間は変わり、TLC が同じ結果を出し直すわけではない。一般化は Lean 側の仕事（[hello-lean-proof の docs/formal-rules.md](https://github.com/nishimotz/hello-lean-proof/blob/main/docs/formal-rules.md)）。

## 試す

```bash
cd docs/compare-pytest
uv run --with pytest pytest -q test_ticket_service.py   # 3 passed（バグを見逃す）
uv run --with pytest pytest -q test_interleaved.py      # 1 failed（自分で思いつけば捕まる）
```

pytest が入っていない環境でも `uv run --with pytest` なら仮想環境を作らずに済む。
