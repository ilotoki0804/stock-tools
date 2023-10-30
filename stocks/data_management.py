from datetime import datetime, timedelta
from typing import Literal

import mojito

DATE_FORMAT = r'%Y%m%d'


def _fetch_prices_unsafe(
    broker: mojito.KoreaInvestment,
    company_code: str,
    date_type: Literal['D', 'W', 'M'],
    start_day: datetime,
    end_day: datetime,
) -> list:
    """day_end 당일은 포함하지 않습니다. 조회할 데이터가 100을 넘어갈 경우의 안전성을 보장하지 않습니다."""
    end_day -= timedelta(1)
    response = broker.fetch_ohlcv(
        company_code, date_type, start_day.strftime(DATE_FORMAT), end_day.strftime(DATE_FORMAT))
    try:
        return response['output2']
    except KeyError:
        raise ValueError(f"Data is not fetched properly. arguments: {(company_code, date_type, start_day.strftime(DATE_FORMAT), end_day.strftime(DATE_FORMAT))},"
                         f"response: {response}")


def fetch_prices_by_datetime(
    broker: mojito.KoreaInvestment,
    company_code: str,
    date_type: Literal['D', 'W', 'M'],
    start_day: datetime,
    end_day: datetime,
) -> list:
    """broker.fetch_ohlcv의 결과값을 조금 더 편리하게 사용할 수 있도록 변경한 함수입니다.

    * string 대신 datetime.datetime을 이용합니다.
    * end_day에 end_day 당일이 포함되지 않습니다.
    """
    result = []

    fraction_start = start_day
    fraction_end = start_day + timedelta(100)  # 100을 넣는다고 조회되는 데이터 수가 100인 건 아니지만(due to 휴일) 최소한 100은 안전하고 계산하기 쉬움.
    while fraction_start < end_day:
        print(fraction_start.strftime(DATE_FORMAT), fraction_end.strftime(DATE_FORMAT))
        result += _fetch_prices_unsafe(broker, company_code, date_type, fraction_start, fraction_end)

        fraction_start = fraction_end
        fraction_end += timedelta(100)
        if fraction_end >= end_day:
            fraction_end = end_day

    return result
