module ticket {
  pure val USERS = Set("alice", "bob", "carol")  // 3人のユーザー
  pure val INITIAL_STOCK = 2                     // チケットは2枚

  type Phase = Idle | Checked | Bought | SoldOut

  // (1) 状態
  var stock: int
  var sold: int
  var phase: str -> Phase

  // (2) 最初の状態
  action init = all {
    stock' = INITIAL_STOCK,
    sold' = 0,
    phase' = USERS.mapBy(_ => Idle),
  }

  // (3) 起こりうる操作
  action check(u: str): bool = all {
    phase.get(u) == Idle,
    phase' = phase.set(u, if (stock > 0) Checked else SoldOut),
    stock' = stock,
    sold' = sold,
  }

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

  // 毎回、誰か1人が「確認」か「確定」をする
  action step = {
    nondet u = USERS.oneOf()
    any { check(u), purchase(u) }
  }

  // (4) ルール：売れた枚数は、最初の在庫数を超えない
  val noOversell = sold <= INITIAL_STOCK
}
