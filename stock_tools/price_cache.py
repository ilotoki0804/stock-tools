from __future__ import annotations
from datetime import datetime, timedelta
import pickle
from typing import Literal
from pathlib import Path

import mojito
import pandas as pd

from .fetch import DATE_FORMAT, _fetch_prices_unsafe, PriceDict
from .exceptions import NoTransactionError
from .key import KEY


MAX_DATE_LIMIT = 100


class PriceCache:
    """Price를 가지고 올 때마다 fetch하지 않고 caching해 더욱 빠르고 간편하게 정보를 가져올 수 있도록 하는 클래스입니다."""

    cache_prices: bool = True
    cache_directory: Path = Path("_cache")

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        if cls.cache_prices:
            self._control_cache_file("load")
        return self

    def __init__(
        self,
        broker: mojito.KoreaInvestment,
        default_company_code: str | None = None,
    ) -> None:
        """company_code가 None이라면 get_price에서 company_code는 생략할 수 없습니다."""
        self.broker = broker
        self.default_company_code = default_company_code
        if not hasattr(self, "_cache"):
            self._standard_day = datetime(1970, 1, 1)
            self._is_standard_day_smartly_defined = False
            self._cache: dict[tuple[str, int], pd.DataFrame] = {}

    @classmethod
    def from_broker_kwargs(
        cls,
        default_company_code: str | None = None,
        **kwargs,
    ) -> PriceCache:
        return cls(mojito.KoreaInvestment(**kwargs), default_company_code)

    @classmethod
    def from_keys_json(
        cls,
        default_company_code: str | None = None,
    ) -> PriceCache:
        return cls(mojito.KoreaInvestment(**KEY), default_company_code)

    def set_standard_day(self, standard_day: datetime) -> None:
        """주의: 기존의 모든 cache가 삭제됩니다. standard_day는 임의의 날짜로 정할 수 있습니다(제약이 없습니다)."""
        self._is_standard_day_smartly_defined = True
        self._standard_day = standard_day
        self._cache.clear()

    def _get_day_category(
        self,
        day: datetime,
    ) -> tuple[int, tuple[datetime, datetime]]:
        date_category, mod = divmod((day - self._standard_day).days, 100)

        start_day = day - timedelta(mod)
        end_day = start_day + timedelta(100)

        return date_category, (start_day, end_day)

    def _control_cache_file(self, action: Literal["store", "delete", "load"]):
        cache_location = self.cache_directory / f"{self.__class__.__name__}.pickle"
        match action:
            case "store":
                self.__class__.cache_directory.mkdir(exist_ok=True, parents=True)
                cache_location.write_bytes(pickle.dumps((self._cache, self._standard_day)))
            case "delete":
                cache_location.unlink(missing_ok=True)
            case "load":
                if cache_location.exists():
                    self._cache, self._standard_day = pickle.loads(cache_location.read_bytes())
                    self._is_standard_day_smartly_defined = True

    def _store_cache_of_day(self, day: datetime, company_code: str) -> int:
        """캐시에 해당 day에 대한 캐시를 저장하고 date_category를 반환합니다."""
        date_category, (start_day, end_day) = self._get_day_category(day)

        if (company_code, date_category) in self._cache:
            return date_category  # Cache hit!

        self._cache[(company_code, date_category)] = pd.DataFrame(
            _fetch_prices_unsafe(self.broker, company_code, "D", start_day, end_day)
        )
        self._control_cache_file("store")
        return date_category

    def _before_get_price(self, day: datetime, company_code: str | None) -> str:
        if not self._is_standard_day_smartly_defined and not self._cache:
            self._standard_day = day - timedelta(50)
            self._is_standard_day_smartly_defined = True

        company_code = company_code or self.default_company_code
        assert company_code, (
            "`company_code` should be specified. "
            "Specify parameter `company code` or set `default_company_code`."
        )

        return company_code

    def get_price(
        self,
        day: datetime,
        company_code: str | None = None,
        nearest_day_threshold: int | None = 0,
        date_direction: Literal["past", "future", "both"] = "both",
    ) -> PriceDict:
        """해당 날짜의 데이터를 가져옵니다. 이때 만약 캐시된 데이터가 있다면 캐시를 사용합니다.
        주의: nearest_day_threshold가 자연수일 때는 NoDateError 대신 NoNearestDateError가 납니다.

        Args:
            nearest_day_threshold:
                장이 쉬는 날의 정보는 받아올 수 없습니다. 이때 get_nearest_data를 True로 하면 가장 가까운 날의 정보를 불러옵니다.
                만약 같은 정보인 경우가 있다면 더 미래의 데이터를 기준으로 잡습니다.
                nearest_day_threshold는 가장 며칠까지 떨어져도 괜찮은지를 설정합니다. 만약 None이라면 가장 가까운 날일 때까지 계속해서 불러옵니다.
                다만 이는 무한 루프를 방지하기 위해 주위 100일로 제한됩니다.
                장이 쉬는 날은 대체로 주말과 공휴일이기 때문에 이틀 이상 떨어지는 일이 드물지만
                기간이 미래이거나 상장 전일 경우 최대 100일 전후의 데이터를 불러올 수도 있습니다.
                nearest_day_threshold가 1이고 date_direction이 'both'라면 주변 1일까지만 허용합니다.
                예를 들어 1월 20일을 받았다면 1월 19일과 1월 21일에 fetch 결과가 없다면 NoNearestDateError가 납니다.
            date_direction:
                nearest_day_threshold가 자연수일 경우 정보를 받아오는 방향을 결정합니다.
                예를 들어 date_direction이 'past'라면 과거로부터의 정보만을 받아오고,
                date_direction이 'future'라면 미래로부터의 정보만을 받아옵니다.
                'both'라면 과거로부터의 가장 현재와 가까운 과거 혹은 미래의 정보를 불러옵니다.
                만약 과거와 현재의 거리가 같다면 과거의 데이터를 우선으로 불러옵니다.
        """

        company_code = self._before_get_price(day, company_code)

        date_category = self._store_cache_of_day(day, company_code)

        price_data = self._cache[(company_code, date_category)]
        result = price_data[price_data["stck_bsop_date"] == day.strftime(DATE_FORMAT)]
        if not result.empty:
            return result.squeeze().to_dict()

        return self._find_suit_day(
            date_direction, nearest_day_threshold, day, company_code
        )

    def _find_suit_day(
        self, date_direction, nearest_day_threshold, day, company_code
    ) -> PriceDict:
        def try_get_price_from(day: datetime):
            try:
                return_value = self.get_price(
                    day, company_code, nearest_day_threshold=0
                )
            except NoTransactionError:
                return None
            else:
                return return_value

        day_diff = None
        nearest_day_threshold = (
            MAX_DATE_LIMIT if nearest_day_threshold is None else nearest_day_threshold
        )
        for day_diff in range(1, nearest_day_threshold + 1):
            if date_direction in {"future", "both"}:
                result = try_get_price_from(day + timedelta(day_diff))
                if result is not None:
                    return result

            if date_direction in {"past", "both"}:
                result = try_get_price_from(day - timedelta(day_diff))
                if result is not None:
                    return result

        if day_diff is None:
            raise NoTransactionError(
                f"When {day}, there's no transaction. "
                "Increase `nearest_day_threshold` if you want to get near data."
            )

        raise NoTransactionError(
            f"There's no transactions between {day - timedelta(day_diff)} "
            f"and {day + timedelta(day_diff)}."
        )

    # def get_prices_between_range(
    #     self,
    #     start_day: datetime,
    #     end_day: datetime,
    #     company_code: str | None = None,
    # ) -> PriceDict:
    #     company_code = self._before_get_price(start_day, company_code)

    #     start_day_category, _ = self._get_day_category(start_day)
    #     end_day_category, _ = self._get_day_category(end_day)
    #     prices = []

    #     curr_day = start_day
    #     while end_day_category <= self._get_day_category(curr_day)[0]:
    #         self._store_cache_of_day(curr_day, company_code)
    #         curr_day += timedelta(100)

    #     for day in

    #     for category in range(start_day_category + 1, end_day_category):

    #     return {}
