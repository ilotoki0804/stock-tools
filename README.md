# stock-project

주식 관련 코드 모음입니다.

## 설치 방법

git을 설치하고 원하는 폴더에 터미널을 연 뒤 `git clone https://github.com/ilotoki0804/stock-project.git`를 치세요.

필요하다면 venv를 설정하고 필요한 패키지를 다운로드받습니다.

> [!WARNING]
> 설치 전 가상 환경이 잘 설치되었는지, 터미널이 가리키고 있는 방향이 루트 디렉토리(LICENSE나 README.md가 있는 폴더)가 맞는지, 파이썬 버전이 3.10 이상인지 확인하세요.

```console
pip install -r requirements.txt
```

### 업데이트

루트 폴더에서 터미널을 열고 `git fetch`를 입력해 주세요.

아무런 메시지도 뜨지 않는다면 이미 최신 상태였다는 의미이고 무언가가 나타난다면 업데이트되었다는 의미입니다.

### keys.json

KEY를 사용하려면 루트 디렉토리에 `keys.json`이 있어야 합니다.

우리 팀의 `keys.json`은 디스코드에 업로드되어 있으니 사용하시면 됩니다.

`keys.json`은 다음과 같은 형식으로 되어 있습니다.

```json
{
    "api_key": "...",
    "api_secret": "...",
    "acc_no": "..."
}
```

설명은 아래의 '사용법'을 참고하세요.

## 사용법

### KEY 사용하기

KEY를 이용하려면 우선 `keys.json`을 폴더에 넣어야 합니다. 자세한 방법은 '설치 방법'을 참고하세요.

`keys.json`이 설치되었다면 다음과 같이 간편하게 mojito를 사용할 수 있습니다.

```python
from stocks import adjust_price_unit, KEY
import mojito

broker = mojito.KoreaInvestment(**KEY)
...
```

### adjust_price_unit 사용하기

`adjust_price_unit`은 지정가 매수 시 호가 단위를 맞출 수 있도록 합니다. 자세한 설명은 `adjust_price_unit`의 docs와 해당 함수가 선언된 모듈의 docs를 참고하세요.

### 매수, 매도 등 사용 및 예제 확인하기

Repo 내 examples.py에는 어떻게 adjust_price_unit를 사용하는지와 매수, 매도를 어떻게 하는 지에 대한 예제가 있습니다. 해당 내용을 참고하세요.

### Transaction Dataclass

Transaction은 한 독립적인 거래를 상징합니다.

#### Transaction의 상태

Transaction의 상태에는 다음과 같은 것들이 있습니다.

* date: 해당 거래가 이루어진 날짜입니다.
* company_code: 해당 회사의 종목 코드입니다.
* amount: 얼마나 사거나 팔았는지를 의미합니다.
    양수라면 매수를 의미하고 음수라면 매도를 의미합니다.
* sell_price: 얼마의 가격에 사거나 팔았는지를 설정합니다.

    이 값은 시가/종가/고가/저가로 정의할 수 있습니다.

    각각 시가는 'open'이고, 종가는 'close', 고가는 'high', 저가는 'low'입니다.

    혹은 직접 정수의 값으로 설정할 수 있습니다. 이때 이 가격은 고가 이하 저가 이상이어야 합니다.

#### Transaction 예시

예를 들어 다음과 같이 Transaction을 정의할 수 있습니다.

```python
from stocks.dataclasses import Transaction
from datetime import datetime

Transaction(
    datetime(2022, 11, 10),  # 2022년 11월 10일에
    '005930',  # 삼성전자를
    3,  # 3개 매수한다.
    'open',  # 일봉의 고가로
)
Transaction(
    datetime(2023, 10, 7),  # 2021년 1월 30일에
    '035720',  # 카카오를
    -24,  # 24개 매도한다.
    43060, # 43060원으로
)
```

### State Dataclass

해당 날짜나 거래 후의 상태를 나타내는 dataclass입니다.

#### State의 상태

State의 상태들은 다음과 같습니다.

* date: 해당하는 날짜입니다.
* total_appraisement: 총 평가액으로, 주식 평가액과 예산을 합친 금액입니다.
* budget: 예산으로, 현재 수중에 돈이 얼마나 있는지를 나타낸 금액입니다.
    이 값을 0으로 놓으면 total_appraisement가 음수일 경우 손실, 양수일 경우 이익이 되어 계산하기에 직관적입니다.
* stocks: 주식들입니다. type은 `dict[str, tuple[int, int]]`로 `dict[종목 코드, tuple[주수, 현재가]]`입니다.
    주수는 음수가 될 수도 있습니다.
* privous_state: 이전 State입니다. None일 수도 있습니다.
* transaction: 해당 State의 stocks가 변경되는 데에 어떤 transaction이 기여했을 때 해당 transaction의 값입니다.

#### State 예시

* 실제로 State를 직접 정의해야 하는 상황은 드믊니다. State가 무엇인지만 알면 충분합니다.

예를 들어 다음과 같이 State를 정의할 수 있습니다.

```python
from stocks.dataclasses import State, Transaction
from datetime import datetime

State(
    date=datetime(2022, 6, 12),  # 2022년 6월 12일
    total_appraisement=994170,  # 총 평가액 994170원 (stocks에 의존하는 값)
    budget=249170,  # 주식 평가액을 포함하지 않은 예산 249170원
    stocks={'086520': (10, 74500)},  # 평가액 74500원의 삼성전자 주식 보유 중
    privous_state=State(...),  # 어떤 privous_state를 가짐
    transaction=None,  # 전 State와 이번 State 사이에 transaction은 없음.
)
```

하지만 직접 State를 정의하는 것은 힘들기 때문에 `State.from_state_and_transaction`을 사용할 수 있습니다.

```python
from stocks import KEY
from stocks.dataclasses import State, Transaction, PriceCache
from datetime import datetime

price_cache = PriceCache.from_broker_kwargs(**KEY)

State.from_state_and_transaction(
    price_cache,
    datetime(2022, 6, 12),  # 2022년 6월 12일
    None,  # 이전 상태 없음
    Transaction(datetime(2023, 7, 15), '035720', -20, 'close'),  # 이러한 Transaction을 사용함.
)
```

### emulate_trade 사용하기

`emulate_trade`는 주식 매매 기록을 받으면 예산이나 주식 평가액 등을 계산해서 답을 내는 함수입니다.

#### 사전 준비

price_cache 인스턴스와 transactions(거래 내역)을 준비합니다.

```python
from datetime import datetime

import pandas as pd

from stocks import KEY, PriceCache, emulate_trade
from stocks.dataclasses import Transaction, State

# 하기 전에 keys.json이 있는지 꼭 확인하세요!!
price_cache = PriceCache.from_broker_kwargs(**KEY)

# 자신이 원하는 거래 내역을 여기에 설정해주세요.
transactions = [
    Transaction(datetime(2022, 6, 10), '086520', 10, 'open'),
    Transaction(datetime(2022, 11, 10), '005930', 3, 'open'),
    Transaction(datetime(2023, 5, 23), '086520', -10, 'close'),
    Transaction(datetime(2023, 5, 23), '035720', 20, 'close'),
    Transaction(datetime(2023, 5, 23), '005930', 4, 'close'),
    Transaction(datetime(2023, 5, 30), '005930', -7, 'close'),
    Transaction(datetime(2023, 7, 15), '035720', -20, 'close'),
]
```

#### 결과 가져오기

price_cache와 transactions를 emulate_trade에 넘깁니다.

주의할 점은 emulate_trade의 결과값은 dataframe이 아닌 `list[State]`이기 때문에 dataframe으로 변경하려면 `pd.DataFrame()`을 통과시켜야 합니다. (추후에 에초에 Dataframe을 return하는 것으로 변경될 가능성이 있습니다.)

```python
result = pd.DataFrame(emulate_trade(price_cache, transactions, initial_state))
# print로 값을 확인하는 것 대신 jupyter notebook을 사용하는 것을 권장합니다.
# 여기에서는 텍스트로 보여주기 위해 print를 사용합니다.
print(result)
#           date  total_appraisement   budget                   stocks  \
# 0   2022-06-09              100000  1000000                       {}   
# 1   2022-06-10             1000000   249170  {'086520': (10, 75083)}   
# 2   2022-06-11              994170   249170  {'086520': (10, 74500)}   
...
# 401                                               None  
# 402                                               None  
# 403  {'date': 2023-07-15 00:00:00, 'company_code': ...  

# [404 rows x 6 columns]
```

`only_if_transaction_exists`가 True일 경우 transaction이 있었던 날의 State만을 불러옵니다.

```python
result = pd.DataFrame(emulate_trade(price_cache, transactions, initial_state, only_if_transaction_exists=True))
# print로 값을 확인하는 것 대신 jupyter notebook을 사용하는 것을 권장합니다.
# 여기에서는 텍스트로 보여주기 위해 print를 사용합니다.
print(result)
#         date  total_appraisement   budget  \
# 0 2022-06-09              100000  1000000   
# 1 2022-06-10             1000000   249170   
# 2 2022-11-10             1509950    64970   
...
# 5  {'date': 2023-05-23 00:00:00, 'company_code': ...  
# 6  {'date': 2023-05-30 00:00:00, 'company_code': ...  
# 7  {'date': 2023-07-15 00:00:00, 'company_code': ...  
```
