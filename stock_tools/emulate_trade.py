from __future__ import annotations
from datetime import datetime, timedelta
from dataclasses import asdict
from typing import overload

import pandas as pd

from .price_cache import PriceCache
from .transaction_and_state import (
    Transaction,
    State,
    INITIAL_STATE,
)


@overload
def emulate_trade(
    price_cache: PriceCache,
    transactions: list[Transaction] | pd.DataFrame,
    initial_state: State | None = None,
    final_date: datetime | None = None,
    only_if_transaction_exists: bool = False,
    commission: tuple[float, float] | None = None,
    panic_sell_rate: None = ...,
) -> list[State]:
    ...


@overload
def emulate_trade(
    price_cache: PriceCache,
    transactions: list[Transaction] | pd.DataFrame,
    initial_state: State | None = None,
    final_date: datetime | None = None,
    only_if_transaction_exists: bool = False,
    commission: tuple[float, float] | None = None,
    panic_sell_rate: float = ...,
) -> tuple[list[State], list[tuple[datetime, float]]]:
    ...


@overload
def emulate_trade(
    price_cache: PriceCache,
    transactions: list[Transaction] | pd.DataFrame,
    initial_state: State | None = None,
    final_date: datetime | None = None,
    only_if_transaction_exists: bool = False,
    commission: tuple[float, float] | None = None,
    panic_sell_rate: float | None = None,
) -> list[State] | tuple[list[State], list[tuple[datetime, float]]]:
    ...


def emulate_trade(
    price_cache: PriceCache,
    transactions: list[Transaction] | pd.DataFrame,
    initial_state: State | None = None,
    final_date: datetime | None = None,
    only_if_transaction_exists: bool = False,
    commission: tuple[float, float] | None = None,
    panic_sell_rate: float | None = None,
) -> list[State] | tuple[list[State], list[tuple[datetime, float]]]:
    """거래를 모사해 거래의 결과와 진행 상황을 확인합니다. transactions와 관련한 설명은 Transaction dataclass를 확인하세요.

    Args:
        price_cache: PriceCache 인스턴스를 입력으로 받습니다.
        transactions: transaction들을 입력으로 받습니다. 혹은 그 값을 Dataframe에 돌린 값도 가능합니다.
            주의: 거래는 반드시 시간 순서대로 정렬되어 있어야 합니다.
        initial_state: 초기 상태를 정합니다. 이것으로 기존에 가지고 있던 주식이나 예산 등도 정의할 수 있습니다.
        only_if_transaction: 이 값이 False라면(기본값) transaction이 없는 날도 계산합니다.
            만약 True라면 Transaction이 있는 날만 계산합니다.
        commission: 주식 수수료를 나타냅니다. 자세한 설명은 State의 docs를 확인하세요.
        panic_sell_rate: 주식 가격이 산 가격 대비 설정한 수준 이하로 떨어지먼 transaction을 무시하고 모든 주식을 털어냅니다.
            예를 들어 panic_sell_rate가 0.3이고 샀을 당시 가격이 1000원이고 현재 가격이 600원이라면
            `(1000 - 700) / 1000 >= 0.3`가 True이기 때문에 무조건 팝니다(panic sell).
            값이 0과 1 사이의 float라면 만약 None이라면 관련 기능이 사용되지 않습니다.
            이 경우 모든 매매는 전부 사거나 파는 것이여야 하며, 매수와 매도가 반복적으로 이루어지는 방식(즉, 시그널)이여야 합니다.

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
    Rs = [(initial_state.date, 0.0)]
    transaction_exist_dates: set[datetime] = set(transactions_df["date"].unique())
    state_after_last_transaction: State | None = None
    # min과 max 대신 transactions_df['date'][0]와 transactions_df['date'][-1]를 사용할 수도 있음.
    start_day_diff = (
        initial_state.date - standard_date
        if initial_state is not INITIAL_STATE
        else min(transaction_exist_dates) - standard_date
    ).days
    end_day_diff = (
        final_date - standard_date
        if final_date is not None
        else max(transaction_exist_dates) - standard_date
    ).days
    for day_diff in range(start_day_diff, end_day_diff + 1):
        date = standard_date + timedelta(day_diff)
        if not only_if_transaction_exists and date not in transaction_exist_dates:
            state = State.from_previous_state(price_cache, date, states[-1], None)
            if state_after_last_transaction is None:
                appraisement_diff_rate = 0.0
            else:
                # (700 - 1000) / 1000
                appraisement_diff_rate = _calculate_appraisement_diff_rate(
                    state_after_last_transaction.total_appraisement
                    - state_after_last_transaction.budget,
                    state.total_appraisement - state_after_last_transaction.budget,
                )

            states.append(state)
            if panic_sell_rate is None:
                continue
            Rs.append((date, appraisement_diff_rate))
            if appraisement_diff_rate > -panic_sell_rate:
                continue

            # -(700 - 1000) / 1000 >= 0.3
            transaction = transactions_df.query("date > @date").iloc[0]
            adjusted_transaction = _adjust_transaction(price_cache, transaction, date)

            transactions_df.loc[
                transactions_df.query("date > @date").index[0]
            ] = pd.Series(asdict(adjusted_transaction))

            # continue를 넣지 말 것! 끝난 후 transaction이 처리될 수 있도록 하기 위함.

        transactions_of_date = transactions_df.query("date == @date")
        # 리스트 컴프리헨션으로 바꾸면 오류가 생기니 하지 말 것.
        for args in transactions_of_date.iloc:
            state = State.from_previous_state(
                price_cache,
                date,
                states[-1],
                Transaction(*args),
                commission=commission,
            )
            states.append(state)
        state_after_last_transaction = states[-1]
    return states if panic_sell_rate is None else (states, Rs)


def _calculate_appraisement_diff_rate(
    stock_appriasement_after_last_transaction: int | float,
    current_stock_appraisement: int | float,
) -> float:
    if stock_appriasement_after_last_transaction == current_stock_appraisement:
        return 0.0

    return (
        current_stock_appraisement - stock_appriasement_after_last_transaction
    ) / stock_appriasement_after_last_transaction


def _adjust_transaction(
    price_cache: PriceCache, transaction: pd.Series | Transaction, new_date: datetime
):
    transaction_dict = (
        asdict(transaction)
        if isinstance(transaction, Transaction)
        else transaction.to_dict()
    )
    del transaction_dict["sell_price"]
    del transaction_dict["_is_sell_price_evaluated"]
    transaction_dict["date"] = new_date

    # 원래는 sell_price나 get_price에 여러가지 설정이 있지만 우선 기본값으로 상정함.
    # 만약 나중에 커스텀이 중요해지는 순간이 오면 수정이 불가피함.
    adjusted_transaction = Transaction(**transaction_dict, sell_price="close")
    adjusted_transaction.evaluate_sell_price(
        price_cache.get_price(
            transaction_dict["date"],
            transaction_dict["company_code"],
            None,
            "past",
        )
    )
    return adjusted_transaction
