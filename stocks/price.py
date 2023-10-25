"""지정가 매수 시 값을 호가단위에 가격을 맞춥니다.

## 호가의 가격 단위

투자자가 주식을 매도할 때 부르는 가격을 매도 호가라고 하고, 매수할 때 부르는 가격을 매수 호가라고 합니다.
그런데 이 호가에는 가격 단위가 존재하며 이 규칙에 맞게 호가를 제출해야 정상적으로 거래가 진행됩니다.
예를 들어, 삼성전자의 현재가가 60,000원이라면 100 단위의 호가만 유효합니다.
즉, 60,100, 60,200원은 정상적인 호가이지만 60,050원은 호가의 가격단위에 맞지 않아서 정상적으로 주문이 진행되지 않습니다.

호가단위는 2023년 1월 25일에 다음과 같이 변경되었습니다.  ETF, ETN, ELW 상품은 5원 단위의 호가가격단위를 사용합니다. 

기준가 | 호가단위
-----|-----
~2,000원 미만 | 1원 
2,000원 이상~5,000원 미만 | 5원
5,000원 이상~20,000원 미만 | 10원
20,000원 이상~50,000원 미만 | 50원
50,000원 이상~200,000원 미만 | 100원 
200,000원 이상~500,000원 미만 | 500원
500,000원 이상 | 1,000원

출처 및 자세한 정보: https://wikidocs.net/165194
"""

from __future__ import annotations
import logging
from typing import Literal, NamedTuple


class PriceUnit(NamedTuple):
    start: int
    stop: int | None
    step: int

    def is_in_range(self, price):
        return self.start <= price and (self.stop is None or price < self.stop)

    def __contains__(self, price):
        if self.stop is None:
            return self.is_in_range(price) and (price - self.start) % self.step == 0
        else:
            return price in range(self.start, self.stop, self.step)


PRICE_UNITS = {PriceUnit(1, 2000, 1), PriceUnit(2000, 5000, 5), PriceUnit(5000, 20000, 10), PriceUnit(20_000, 50_000, 50),
               PriceUnit(50_000, 200_000, 1000), PriceUnit(200_000, 500_000, 500), PriceUnit(500_000, None, 1000)}


def adjust_price_unit(
    price: int,
    mode: Literal['round', 'floor', 'ceil'] = 'round',
    error: bool = False,
    alert: bool = False,
) -> int:
    """호가 단위에 가격을 맞춥니다.

    Args:
        price (int): 가격입니다. 이 값을 호가 단위에 맞추어 반환합니다.
        mode (Literal['round', 'floor', 'ceil'], optional): 호가 단위를 맞출 때 어떤 방식으로 할 지를 결정합니다. Defaults to 'round'.
            'round'일 경우:
                2,000원 이상~5,000원 미만 구간에서의 호가 단위는 5원입니다.
                즉, 2005원이나 2310원을 호가할 수는 있지만 4903원이나 2014원을 호가할 수는 없습니다.
                이때 호가할 수 없는 값을 price에 들여보내면 반올림됩니다.
                예를 들어 2003원은 2005원으로, 4282원은 4280원으로 반올림됩니다.
                만약 호가 단위가 짝수이고 그 가운데에 온다면 더 작은 값으로 반올림됩니다.
                예를 들어 5005원은 5010원이 됩니다.
            'floor'일 경우:
                호가할 수 없는 값을 price에 들여보내면 내림합니다.
            'ceil'일 경우:
                호가할 수 없는 값을 price에 들여보내면 올림합니다.
        error (bool, optional): True이면 호가 단위에 맞지 않는 price가 올 경우 error를 냅니다. Defaults to False.
        alert (bool, optional): True이면 호가 단위에 맞지 않는 price가 올 경우 경고합니다. Defaults to True.

    Raises:
        TypeError: 적절한 mode가 오지 않는다면 발생합니다.
        ValueError: price가 적절한 호가 단위에 있지 않고, error가 True일 경우 발생합니다.

    Returns:
        int: 호가 단위에 맞춰진 값을 내보냅니다. 이 값은 mode에 상관없이 지정가 매매 시 안전합니다.
    """
    curr_price_unit = None
    is_price_unit_matched = False
    for price_unit in PRICE_UNITS:
        if price_unit.is_in_range(price):
            curr_price_unit = price_unit
            is_price_unit_matched = price in price_unit

    assert curr_price_unit is not None, 'No matched price unit. Code has vulnerability.'

    if is_price_unit_matched:
        return price

    diff = (price - curr_price_unit.start) % curr_price_unit.step
    if mode == 'round':
        if curr_price_unit.step / 2 <= diff:
            adjusted_price = price - diff + curr_price_unit.step
        else:
            adjusted_price = price - diff
    elif mode == 'floor':
        adjusted_price = price - diff
    elif mode == 'ceil':
        adjusted_price = price - diff + curr_price_unit.step
    else:
        raise TypeError(f"Unknown mode '{mode}'.")

    if error:
        raise ValueError(f"Price is not matched in any price unit. Adjust value in order to match price unit like: {adjusted_price}({mode} mode).")
    if alert:
        logging.warning(f"Price is not matched in any price unit. Price has been adjusted from {price} to {adjusted_price}({mode} mode).")
    return adjusted_price
