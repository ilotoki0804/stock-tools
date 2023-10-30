from datetime import datetime, timedelta
from typing import Literal

import mojito
import pandas as pd

from .data_management import DATE_FORMAT, _fetch_prices_unsafe
from .exceptions import NoTransactionError


MAX_DATE_LIMIT = 100


class PriceCache:
    def __init__(self, broker: mojito.KoreaInvestment, default_company_code: str | None = None) -> None:
        """company_code가 None이라면 get_price에서 company_code는 생략할 수 없습니다."""
        self.broker = broker
        self.default_company_code = default_company_code
        self._standard_day = datetime(1970, 1, 1)
        self._is_standard_day_smartly_defined = False
        self._cache: dict[tuple[str, int], list] = {}

    def set_standard_day(self, standard_day: datetime):
        """주의: 기존의 모든 cache가 삭제됩니다. standard_day는 임의의 날짜로 정할 수 있습니다(제약이 없습니다)."""
        self._standard_day = standard_day
        self._cache.clear()

    @staticmethod
    def _get_day_category(day: datetime, standard_day: datetime) -> tuple[int, tuple[datetime, datetime]]:
        date_category, mod = divmod((day - standard_day).days, 100)

        start_day = day - timedelta(mod)
        end_day = start_day + timedelta(100)

        return date_category, (start_day, end_day)

    def _store_cache_of_day(self, day: datetime, company_code: str) -> int:
        """캐시에 해당 day에 대한 캐시를 저장하고 date_category를 반환합니다."""
        date_category, (start_day, end_day) = self._get_day_category(day, self._standard_day)

        if (company_code, date_category) in self._cache:
            return date_category  # Cache hit!

        self._cache[(company_code, date_category)] = _fetch_prices_unsafe(self.broker, company_code, 'D', start_day, end_day)
        return date_category

    def get_price(
        self,
        day: datetime,
        company_code: str | None = None,
        nearest_day_threshold: int | None = 0,
        date_direction: Literal['past', 'future', 'both'] = 'both'
    ) -> tuple[dict, datetime]:
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
        if not self._is_standard_day_smartly_defined:
            self._standard_day = day - timedelta(50)
            self._is_standard_day_smartly_defined = True

        company_code = company_code or self.default_company_code
        assert company_code, '`company_code` should be specified. Give `company code` to parameter or set `default_company_code`.'

        date_category = self._store_cache_of_day(day, company_code)

        price_data = pd.DataFrame(self._cache[(company_code, date_category)])  # TODO: dataframe을 미리 만들어서 넣기
        result = price_data[price_data['stck_bsop_date'] == day.strftime(DATE_FORMAT)]
        if not result.empty:
            return result.squeeze().to_dict(), day

        day_diff = None
        for day_diff in range(1, (MAX_DATE_LIMIT if nearest_day_threshold is None else nearest_day_threshold) + 1):
            if date_direction in {'future', 'both'}:
                try:
                    return_value = self.get_price(day + timedelta(day_diff), company_code, nearest_day_threshold=0)
                except NoTransactionError:
                    pass
                else:
                    print(f'Get price from {day + timedelta(day_diff)} instead {day}.')
                    return return_value

            if date_direction in {'past', 'both'}:
                try:
                    return_value = self.get_price(day - timedelta(day_diff), company_code, nearest_day_threshold=0)
                except NoTransactionError:
                    pass
                else:
                    print(f'Get price from {day - timedelta(day_diff)} instead {day}.')
                    return return_value

        if day_diff is None:
            raise NoTransactionError(f"When {day}, there's no transaction. "
                                     "Increase `nearest_day_threshold` if you want to get near data.")

        raise NoTransactionError(f"There's no transactions between {day - timedelta(day_diff)} and {day + timedelta(day_diff)}.")
