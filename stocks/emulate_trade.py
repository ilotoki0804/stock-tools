from datetime import datetime, timedelta

import mojito
import pandas as pd

from . import PriceCache
from .dataclasses import SIGNIFICANT_PRICE_NAMES, Transaction, State, INITIAL_STATE


def emulate_trade(
    broker: mojito.KoreaInvestment,
    transactions: list[Transaction],
    initial_state: State | None = None,
    only_if_transaction: bool = False,
) -> list[State]:
    """거래를 모사해 거래의 결과와 진행 상황을 확인합니다. transactions와 관련한 설명은 Transaction dataclass를 확인하세요.

    주의: 거래는 반드시 시간 순서대로 정렬되어 있어야 합니다.
    """
    price_cache = PriceCache(broker)
    standard_date = datetime(1970, 1, 1)
    initial_state = initial_state or INITIAL_STATE

    transactions_df = pd.DataFrame(transactions)

    states = [INITIAL_STATE]
    dates: set[datetime] = set(transactions_df['date'].unique())
    # min과 max 대신 transactions_df['date'][0]와 transactions_df['date'][-1]를 사용할 수도 있음.
    for day_diff in range((min(dates) - standard_date).days, (max(dates) - standard_date).days + 1):
        date = standard_date + timedelta(day_diff)
        if not only_if_transaction and date not in dates:
            states.append(State.easy_make(price_cache, date, states[-1], None))
            continue

        transactions_of_this_date = transactions_df[transactions_df['date'] == date]
        # sourcery skip
        for i in range(len(transactions_of_this_date.index)):  # df.index는 1부터 시작할 수도 있지만 iloc은 무조건 0부터 시작함.
            states.append(
                State.easy_make(
                    price_cache,
                    date,
                    states[-1],
                    Transaction(*transactions_of_this_date.iloc[i - 1])
                )
            )

    return states
