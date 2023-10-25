# stock-project

주식 관련 코드 모음입니다.

## 설치 방법

git을 설치하고 원하는 폴더에 터미널을 열고 `git clone https://github.com/ilotoki0804/stock-project.git`를 치세요.

그런 뒤 필요하다면 venv를 설정하고 필요한 패키지를 다운로드받습니다.

> [!WARNING]
> 설치 전 가상 환경이 잘 설치되었는지, 터미널이 가리키고 있는 방향이 루트 디렉토리(LICENSE나 README.md가 있는 폴더)가 맞는지 확인하세요.

```console
pip install -r requirements.txt
```

### keys.json

KEY를 사용하려면 루트 디렉토리에 `keys.json`이 있어야 합니다.

우리 팀의 `keys.json`은 디스코드에 업로드되어 있으니 사용하시면 됩니다.

`keys.json`은 다음과 같은 형식으로 되어 있습니다.

```json
{
    "api_key": ...,
    "api_secret": ...,
    "acc_no": ...
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
