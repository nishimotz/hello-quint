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
