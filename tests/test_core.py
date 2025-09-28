from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading.core import (
    Order,
    OrderFactory,
    OrderSide,
    OrderType,
    Trader,
    OrderBook,
    MatchingEngine,
)


def test_order_creation_limit():
    o = OrderFactory.create_limit(
        order_id="o1",
        side=OrderSide.BUY,
        price=100.0,
        quantity=5.0,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    assert o.id == "o1"
    assert o.type is OrderType.LIMIT
    assert o.side is OrderSide.BUY
    assert o.price == 100.0
    assert o.quantity == 5.0


def test_order_creation_market_validation():
    # Creating a MARKET order with a non-None price should raise
    with pytest.raises(ValueError):
        Order(
            id="o2",
            type=OrderType.MARKET,
            side=OrderSide.SELL,
            price=1.0,
            quantity=1.0,
            timestamp=datetime.now(tz=timezone.utc),
        )


def test_trader_balance_and_positions():
    t = Trader(trader_id="t1", balance=100.0)
    t.deposit(50)
    assert t.balance == 150.0
    with pytest.raises(ValueError):
        t.withdraw(1000)
    t.update_position("AAPL", 10)
    t.update_position("AAPL", -10)
    assert "AAPL" not in t.positions


def test_order_book_add_remove_and_sorting():
    ob = OrderBook(symbol="AAPL")
    o1 = OrderFactory.create_limit("b1", OrderSide.BUY, 100.0, 1)
    o2 = OrderFactory.create_limit("b2", OrderSide.BUY, 101.0, 1)
    o3 = OrderFactory.create_limit("a1", OrderSide.SELL, 102.0, 1)
    ob.add_order(o1)
    ob.add_order(o2)
    ob.add_order(o3)
    assert ob.bids[0].id == "b2"  # highest first
    assert ob.asks[0].id == "a1"  # lowest first
    removed = ob.remove_order("b1")
    assert removed and removed.id == "b1"


def test_matching_engine_basic_match():
    ob = OrderBook(symbol="AAPL")
    me = MatchingEngine(order_book=ob)
    ob.add_order(OrderFactory.create_limit("b1", OrderSide.BUY, 101.0, 2))
    ob.add_order(OrderFactory.create_limit("a1", OrderSide.SELL, 100.5, 1))
    # matching is triggered on add; check result
    assert len(me.trades) == 1
    tr = me.trades[0]
    assert tr.quantity == 1
    assert tr.price == 100.5
    # order book updated: bid reduced to 1, ask removed
    assert ob.bids[0].quantity == 1
    assert len(ob.asks) == 0


