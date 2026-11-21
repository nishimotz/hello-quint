from ticket_service import TicketService

USERS = ["alice", "bob", "carol"]


def test_interleaved_check_purchase():
    svc = TicketService(2, USERS)
    svc.check("alice"); svc.purchase("alice")   # 在庫1
    svc.check("bob")                            # bob は在庫1を見て Checked
    svc.check("carol"); svc.purchase("carol")   # carol が最後の1枚を買う
    svc.purchase("bob")                         # それでも bob は買える → 売り越し
    assert svc.stock >= 0
