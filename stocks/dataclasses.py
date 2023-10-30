from datetime import datetime, timedelta
from typing import Literal, Annotated
from dataclasses import dataclass
import logging

from . import PriceCache
from .exceptions import InvalidPriceError

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

    def evaluate_sell_price(self, price: dict) -> None:
        """이 함수를 실행하면 sell_price가 무조건 정수 가격이 됩니다."""
        if self._is_sell_price_evaluated:
            return

        if isinstance(self.sell_price, str):
            self.sell_price = int(price[SIGNIFICANT_PRICE_NAMES[self.sell_price]])
            self.is_sell_price_evaluated = True
            return

        if (
            price[SIGNIFICANT_PRICE_NAMES["low"]]
            <= self.sell_price
            <= price[SIGNIFICANT_PRICE_NAMES["high"]]
        ):
            return

        raise InvalidPriceError(
            "Manual sell_price should be lower then or equal to highest price and greater then or equal to lowest price in daily."
            f"sell_price: {self.sell_price}, highest price: {SIGNIFICANT_PRICE_NAMES['high']}, lowest price: {SIGNIFICANT_PRICE_NAMES['low']}"
        )


@dataclass
class State:
    """해당 날짜나 거래 후의 상태를 나타내는 dataclass입니다.

    stocks의 count는 음수가 될 수도 있습니다.
    """

    date: datetime
    total_appraisement: int
    budget: int
    stocks: dict[str, tuple[Annotated[int, "count"], Annotated[int, "price"]]]
    privous_state: "State | None"
    transaction: Transaction | None

    @classmethod
    def from_state_and_transaction(
        cls,
        price_cache: PriceCache,
        date: datetime,
        privous_state: "State | None",
        transaction: Transaction | None,
    ) -> "State":
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
            )[0]

            transaction.evaluate_sell_price(evaluated_price)
            assert isinstance(
                transaction.sell_price, int
            ), "Maybe evaluate_sell_price didn't work well."

            new_stock_count = (
                privous_state.stocks.get(transaction.company_code, (0, transaction.sell_price))[0]
                + transaction.amount
            )
            if new_stock_count == 0:
                stocks = privous_state.stocks.copy()
                try:
                    del stocks[transaction.company_code]
                except KeyError:
                    print(f"KeyError occured. {stocks=}, {transaction.company_code=}")
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
                price_cache.get_price(date, company_code, None, "past")[0][
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
