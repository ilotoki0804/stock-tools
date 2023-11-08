from __future__ import annotations
from datetime import datetime, timedelta
import logging
from typing import Literal, TypedDict

import mojito

from .exceptions import MojitoInvalidResponseError

DATE_FORMAT = r"%Y%m%d"


class PriceDict(TypedDict):
    stck_bsop_date: str
    stck_clpr: str
    stck_oprc: str
    stck_hgpr: str
    stck_lwpr: str
    acml_vol: str
    acml_tr_pbmn: str
    flng_cls_code: str
    prtt_rate: str
    mod_yn: str
    prdy_vrss_sign: str
    prdy_vrss: str
    revl_issu_reas: str


def _fetch_prices_unsafe(
    broker: mojito.KoreaInvestment,
    company_code: str,
    date_type: Literal["D", "W", "M"],
    start_day: datetime,
    end_day: datetime,
) -> list[PriceDict]:
    """fetch_prices_by_datetime와 거의 같지만 조회할 데이터가 100을 넘어갈 경우의 안전성을 보장하지 않습니다."""
    end_day -= timedelta(1)
    if (start_day - end_day).days >= 100 and date_type == "D":
        logging.warning("Unsafe operation. Data can be truncated. Use `fetch_prices_by_datetime` to make operation safe.")
    response = broker.fetch_ohlcv(
        company_code,
        date_type,
        start_day.strftime(DATE_FORMAT),
        end_day.strftime(DATE_FORMAT),
    )
    try:
        if response["output2"][0] == {}:
            error_massage = "data received from mojito is invalid. Try again later is only solution currently."
            if all(price == {} for price in response["output2"]):
                error_massage = "All of the " + error_massage
            else:
                error_massage = "The " + error_massage
            raise MojitoInvalidResponseError(error_massage)
        return response["output2"]
    except KeyError:
        values = company_code, date_type, start_day.strftime(DATE_FORMAT), end_day.strftime(DATE_FORMAT)
        raise ValueError(f"Data is not fetched properly. arguments: {values}, response: {response}")


def fetch_prices_by_datetime(
    broker: mojito.KoreaInvestment,
    company_code: str,
    date_type: Literal["D", "W", "M"],
    start_day: datetime,
    end_day: datetime,
) -> list[PriceDict]:
    """broker.fetch_ohlcv의 결과값을 조금 더 편리하게 사용할 수 있도록 변경한 함수입니다.

    * string 대신 datetime.datetime을 이용합니다.
    * end_day에 end_day 당일이 포함되지 않습니다.
    * 쿼리가 100개가 넘더라도 상관없이 불러옵니다.
    """
    result = []

    fraction_start = start_day
    # 100을 넣는다고 조회되는 데이터 수가 100인 건 아니지만(due to 휴일) 최소한 100은 안전하고 계산하기 쉬움.
    fraction_end = start_day + timedelta(100)
    while fraction_start < end_day:
        print(fraction_start.strftime(DATE_FORMAT), fraction_end.strftime(DATE_FORMAT))
        result += _fetch_prices_unsafe(
            broker, company_code, date_type, fraction_start, fraction_end
        )

        fraction_start = fraction_end
        fraction_end += timedelta(100)
        if fraction_end >= end_day:
            fraction_end = end_day

    return result
