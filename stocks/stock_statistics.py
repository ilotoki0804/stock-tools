import logging
from typing import Literal
from datetime import datetime
import statistics

import mojito
import pandas as pd

from .fetch import fetch_prices_by_datetime
from .transaction_and_state import State, SIGNIFICANT_PRICE_NAMES


def MDD(states: list[State] | pd.DataFrame) -> float:
    states = pd.DataFrame(states) if isinstance(states, list) else states
    total_appraisement = states["total_appraisement"]
    max_appraisement = total_appraisement.max()
    min_appraisement = total_appraisement.min()
    if total_appraisement.iloc[0] == 0:
        logging.warning("Budget starts with zero, so the value can be nonprecise.")
    elif min_appraisement < 0:
        logging.warning("Minimum value is negative, so the value can be nonprecise."
                        f"min: {min_appraisement}")
    return (max_appraisement - min_appraisement) / max_appraisement


def CAGR(states: list[State] | pd.DataFrame) -> float:
    """1년은 윤년과는 상관없이 356일로 계산합니다."""
    if isinstance(states, list):
        first_day = states[0]
        last_day = states[-1]
        getter = getattr
    else:
        first_day = states.iloc[0]
        last_day = states.iloc[-1]
        getter = lambda x, y: x[y]  # noqa: E731

    if getter(first_day, "budget") == 0:
        raise ValueError("Initial budget was 0, thus cannot get CAGR")

    total_earning_multiple: int = (
        getter(last_day, "total_appraisement")
        - getter(first_day, "total_appraisement")
    ) / getter(first_day, "budget")
    years_diff: float = (
        getter(last_day, "date") - getter(first_day, "date")
    ).days / 365

    return total_earning_multiple ** (1 / years_diff) - 1


def stock_volatility(
    broker: mojito.KoreaInvestment,
    company_code: str,
    date_type: Literal["D", "W", "M"],
    start_day: datetime,
    end_day: datetime,
    price_from: str = "open",
):
    """시작일과 종료일 모두를 포함합니다. 주의: 이 함수는 버그가 있을 수 있습니다."""

    price_change_rates = []
    prev_single_price = None
    for price in fetch_prices_by_datetime(
        broker, company_code, date_type, start_day, end_day
    ):
        single_price = int(price[SIGNIFICANT_PRICE_NAMES[price_from]])

        if prev_single_price is not None:
            print(f"{single_price - prev_single_price=}, {single_price=}, "
                  f"{(single_price - prev_single_price) / single_price=}")
            price_change_rates.append((single_price - prev_single_price) / single_price)

        prev_single_price = single_price
    return statistics.stdev(price_change_rates)
