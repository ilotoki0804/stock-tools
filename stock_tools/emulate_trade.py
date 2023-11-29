from __future__ import annotations
from datetime import datetime, timedelta

import pandas as pd

from .price_cache import PriceCache
from .transaction_and_state import (
    Transaction,
    State,
    INITIAL_STATE,
)


def emulate_trade(
    price_cache: PriceCache,
    transactions: list[Transaction] | pd.DataFrame,
    initial_state: State | None = None,
    final_date: datetime | None = None,
    only_if_transaction_exists: bool = False,
    commission: tuple[float, float] | None = None,
) -> list[State]:
    """거래를 모사해 거래의 결과와 진행 상황을 확인합니다. transactions와 관련한 설명은 Transaction dataclass를 확인하세요.

    Args:
        price_cache: PriceCache 인스턴스를 입력으로 받습니다.
        transactions: transaction들을 입력으로 받습니다. 혹은 그 값을 Dataframe에 돌린 값도 가능합니다.
            주의: 거래는 반드시 시간 순서대로 정렬되어 있어야 합니다.
        initial_state: 초기 상태를 정합니다. 이것으로 기존에 가지고 있던 주식이나 예산 등도 정의할 수 있습니다.
        only_if_transaction: 이 값이 False라면(기본값) transaction이 없는 날도 계산합니다.
            만약 True라면 Transaction이 있는 날만 계산합니다.
        commission: 주식 수수료를 나타냅니다. 자세한 설명은 State의 docs를 확인하세요.

    Returns:
        State의 list를 반환합니다. Dataframe이 아니라는 점을 주의하세요.
        해당 리스트는 시간 순서대로 배열되지만 만약 해당 날짜에 transaction이 여러 개 있다면 date가 겹칠 수 있습니다.
    """
    standard_date = datetime(1970, 1, 1)
    initial_state = initial_state or INITIAL_STATE

    transactions_df = (
        pd.DataFrame(transactions) if isinstance(transactions, list) else transactions
    )

    states = [initial_state]
    dates: set[datetime] = set(transactions_df["date"].unique())
    # min과 max 대신 transactions_df['date'][0]와 transactions_df['date'][-1]를 사용할 수도 있음.
    start_day_diff = (
        initial_state.date - standard_date
        if initial_state is not INITIAL_STATE
        else min(dates) - standard_date
    ).days
    end_day_diff = (
        final_date - standard_date
        if final_date is not None
        else max(dates) - standard_date
    ).days
    for day_diff in range(start_day_diff, end_day_diff + 1):
        date = standard_date + timedelta(day_diff)
        if not only_if_transaction_exists and date not in dates:
            states.append(
                State.from_previous_state(price_cache, date, states[-1], None)
            )
            continue

        transactions_of_this_date = transactions_df[transactions_df["date"] == date]
        # 리스트 컴프리헨션으로 바꾸면 오류가 생기니 하지 말 것.
        states.extend(
            State.from_previous_state(
                price_cache,
                date,
                states[-1],
                Transaction(*args),
                commission=commission,
            )
            for args in transactions_of_this_date.iloc
        )
    return states
