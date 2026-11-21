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
