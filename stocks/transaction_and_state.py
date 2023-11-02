from __future__ import annotations
from datetime import datetime, timedelta
from typing import Literal, Annotated
from dataclasses import dataclass
import logging

import numpy as np

from . import PriceCache, adjust_price_unit
from .exceptions import InvalidPriceError
from .fetch import PriceDict

SIGNIFICANT_PRICE_NAMES = {
    "low": "stck_lwpr",
    "high": "stck_hgpr",
    "open": "stck_oprc",
    "close": "stck_clpr",
}


@dataclass
class Transaction:
    """
    한 매수/매도 거래를 나타내는 dataclass입니다.
    Transaction에 포함된 내용은 다음과 같습니다:
        date: 거래가 이루어진 날짜를 의미합니다.
        company_code: '005930'과 같은 종목 코드를 의미합니다.
        amount: 거래를 한 양을 의미합니다. 양수일 경우 매수, 음수일 경우 매도로 간주됩니다.
        sell_price: 해당 주식을 판 가격입니다.
            고가, 저가, 시가, 종가 중에 선택할 수 있고, 만약 값을 직접 설정하고 싶다면 직접 가격을 입력할 수 있습니다.
            직접 설정한 가격이 고가보다 높거나 저가보다 낮으면 `InvalidPriceError`를 냅니다.
    """

    date: datetime
    company_code: str
    amount: int
    sell_price: Literal["low", "high", "open", "close"] | int
    _is_sell_price_evaluated: bool = False

    def evaluate_sell_price(
        self,
        price: PriceDict,
        check_price_unit: bool = False,
        alert: bool = True,
        **adjust_price_unit_kwargs
    ) -> None:
        """이 함수를 실행하면 sell_price가 무조건 정수 가격이 됩니다.

        Args:
            price: 해당 날짜의 시가/종가/고가/저가 데이터가 담긴 딕셔너리입니다.
            check_price_unit: 해당 값이 price_unit에 맞는지 확인합니다.
            alert: adjust_price_unit 함수의 파라미터로 사용됩니다.
                adjust_price_unit과는 달리 기본값이 True입니다.
            **kwargs: adjust_price_unit 함수의 파라미터들입니다.
        """
        if self._is_sell_price_evaluated:
            return

        if isinstance(self.sell_price, str):
            # 주식 시장에서 온 값은 항상 다양한 주가 정책을 만족하기 때문에 다른 검사가 필요하지 않다.
            self.sell_price = int(price[SIGNIFICANT_PRICE_NAMES[self.sell_price]])
            return

        # numpy의 int64는 int의 subclass가 아니기에 각종 assertion에서 별별 오류를 다 만들어 냄.
        # 이 구문으로 int64를 python integer로 변경함.
        self.sell_price = int(self.sell_price)
        if not (
            int(price[SIGNIFICANT_PRICE_NAMES["low"]])
            <= self.sell_price
            <= int(price[SIGNIFICANT_PRICE_NAMES["high"]])
        ):
            raise InvalidPriceError(
                "Manual sell_price should be lower then or equal to highest price and greater then or equal to lowest price in daily."
                f"sell_price: {self.sell_price}, highest price: {SIGNIFICANT_PRICE_NAMES['high']}, lowest price: {SIGNIFICANT_PRICE_NAMES['low']}"
            )

        if check_price_unit:
            self.sell_price = adjust_price_unit(self.sell_price, alert=alert, **adjust_price_unit_kwargs)
        self.is_sell_price_evaluated = True
        return


@dataclass
class State:
    """해당 날짜나 거래 후의 상태를 나타내는 dataclass입니다.

    stocks의 count는 음수가 될 수도 있습니다.
    """

    date: datetime
    total_appraisement: int
    budget: int
    stocks: dict[str, tuple[Annotated[int, "count"], Annotated[int, "price"]]]
    privous_state: State | None
    transaction: Transaction | None

    @classmethod
    def from_previous_state(
        cls,
        price_cache: PriceCache,
        date: datetime,
        privous_state: State | None,
        transaction: Transaction | None,
        validate_stock_count: bool = True,
    ) -> State:
        """몇 가지 정보를 주면 total_appraisement나 stocks을 계산해 주는 constructor입니다."""
        if privous_state is None:
            budget = 0
            stocks = {}
            transaction_company = None
        elif transaction is None:
            budget = privous_state.budget
            stocks = privous_state.stocks
            transaction_company = None
        else:
            evaluated_price = price_cache.get_price(
                date, transaction.company_code, None, "past"
            )

            transaction.evaluate_sell_price(evaluated_price)
            assert isinstance(
                transaction.sell_price, int
            ), "Maybe evaluate_sell_price didn't work well."

            new_stock_count = (
                privous_state.stocks.get(transaction.company_code, (0, 0))[0]
                + transaction.amount
            )
            if new_stock_count == 0:
                # 딕셔너리의 값을 변경하기 때문에 .copy()가 필수적임.
                stocks = privous_state.stocks.copy()
                try:
                    del stocks[transaction.company_code]
                except KeyError:
                    print(f"KeyError occured. {stocks=}, {transaction.company_code=}")
            elif validate_stock_count and new_stock_count < 0:
                raise ValueError(f"Stock count cannot be below zero. "
                                 f"The number of {transaction.company_code} is {new_stock_count}.")
            else:
                stocks = privous_state.stocks | {
                    transaction.company_code: (new_stock_count, transaction.sell_price)
                }

            budget = privous_state.budget - transaction.amount * transaction.sell_price
            transaction_company = transaction.company_code

        new_stocks = {}
        stock_appraisement: int = 0
        for company_code, (count, price) in stocks.items():
            assert isinstance(price, int)
            if transaction_company == company_code:
                new_stocks[company_code] = count, price
                stock_appraisement += count * price
                continue

            # 주식 가격은 str으로 오기 때문에 int로 바꿔줘야 함.
            evaluated_single_price = int(
                price_cache.get_price(date, company_code, None, "past")[
                    SIGNIFICANT_PRICE_NAMES["close"]
                ]
            )

            new_stocks[company_code] = count, evaluated_single_price
            stock_appraisement += count * evaluated_single_price

        return cls(
            date,
            budget + stock_appraisement,
            budget,
            new_stocks,
            privous_state,
            transaction,
        )


INITIAL_STATE = State(datetime(1900, 1, 1), 0, 0, {}, None, None)
