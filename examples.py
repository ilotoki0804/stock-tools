from stocks import adjust_price_unit, KEY
import mojito

# ======================
# adjust_price_unit 관련

print(adjust_price_unit(123_456_789))
print(adjust_price_unit(12_345))
print(adjust_price_unit(12_345, mode='floor'))
print(adjust_price_unit(12_345, mode='floor', alert=True))
try:
    print(adjust_price_unit(12_345, mode='floor', error=True))
except ValueError as e:
    print('error:', e)

# ==============
# 매수, 매도 관련

broker = mojito.KoreaInvestment(**KEY)

# 잔고 조회
balance_res = broker.fetch_balance()

# 지정가 매수
order_by_price_res = broker.create_limit_buy_order(
    symbol="005930",
    price=adjust_price_unit(65000),  # adjust_price_unit 사용
    quantity=1
)

# 시장가 매수
order_by_market_price_res = broker.create_market_buy_order(
    symbol="005930",
    quantity=10
)

# 지정가 매도
sell_by_price_res = broker.create_limit_sell_order(
    symbol="005930",
    price=adjust_price_unit(67000),
    quantity=1
)

# 시장가 매도
sell_by_market_price_res = broker.create_market_sell_order(
    symbol="005930",
    quantity=1
)
