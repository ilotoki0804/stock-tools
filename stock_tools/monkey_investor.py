from datetime import datetime, timedelta
from typing import Literal, Annotated
import random

from .price_cache import PriceCache
from .transaction_and_state import SIGNIFICANT_PRICE_NAMES, Transaction, State


def monkey_investor(
    price_cache: PriceCache,
    company_code: str,
    start_day: datetime,
    end_day: datetime,
    invest_amount: tuple[Annotated[float, "counts"],
                         Annotated[float, "standard_deviation"]],
    total_invest_count: int,
    seed: int | None = None,
) -> tuple[PriceCache, list[Transaction], State, datetime]:
    """
    Args:
        end_day: 마지막 날을 의미합니다. fetch_prices_by_datetime과는 달리 당일을 포함합니다.
        invest_amount: 투자를 한 번에 얼마나 할 지 결정합니다.
            값은 튜플인데, 첫 번째 값은 평균적으로 몇 주를 사고팔지 결정하고, 두 번째 값은 표준편자를 의미합니다.
            예를 들어 값이 (10, 3)이라면 10이 평균, 3이 표준편차인 랜덤값을 반올림한 값을 이용합니다.
        total_invest_count: 이 값을 사용하면 총 투자수를 결정합니다.
        seed: 랜덤값의 시드를 설정합니다. 만약 seed가 None이 아니고 다른 인자의 값이
            모두 같은 두 함수의 결과값이 있다면 그 값은 항상 동일합니다.
    """
    seeded_random = random.Random(seed)

    standard_day = datetime(1970, 1, 1)
    day_range = range((start_day - standard_day).days,
                      (end_day - standard_day).days + 1)

    total_amount = 0
    transactions: list[Transaction] = []
    for transaction_day_diff in sorted(
        seeded_random.choices(day_range, k=total_invest_count)
    ):
        transaction_day = standard_day + timedelta(transaction_day_diff)

        # normalvariate의 결과값이 음수여도 상관없음.
        buy_or_sell = 1 if total_amount == 0 else seeded_random.choice((1, -1))
        transaction_amount = round(seeded_random.normalvariate(*invest_amount)
                                   * buy_or_sell)
        if total_amount + transaction_amount < 0:
            transaction_amount = -total_amount
        total_amount += transaction_amount

        price = price_cache.get_price(transaction_day, company_code, None, "past")
        transaction_price = seeded_random.randint(
            int(price[SIGNIFICANT_PRICE_NAMES["low"]]),
            int(price[SIGNIFICANT_PRICE_NAMES["high"]]),
        )

        transactions.append(Transaction(transaction_day, company_code,
                                        transaction_amount, transaction_price))

    if transactions:
        # 마지막 거래에서는 모든 주식을 청산하도록 함.
        transactions[-1].amount -= total_amount

    initial_state = State.from_previous_state(price_cache, start_day, None, None)
    # return emulate_trade(price_cache, transactions, initial_state, end_day)
    return (price_cache, transactions, initial_state, end_day)
