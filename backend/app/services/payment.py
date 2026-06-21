"""결제 게이트웨이 연동 서비스 (신규).

settings.payment_api_key 환경 변수를 사용한다.
이 키가 배포 환경에 주입되지 않으면 결제가 실패한다.
(변경 영향도 데모: scenario/env-var-change)
"""

from app.config import settings


def is_payment_configured() -> bool:
    """결제 API 키가 운영용으로 주입되었는지 확인한다."""
    return bool(settings.payment_api_key) and settings.payment_api_key != "dev-payment-key"


def authorize_payment(amount: int) -> dict[str, object]:
    """결제 승인 요청(데모용 스텁). 실제로는 외부 게이트웨이를 호출한다."""
    if not is_payment_configured():
        raise RuntimeError(
            "PAYMENT_API_KEY 가 주입되지 않았습니다. 배포 환경 변수 설정을 확인하세요."
        )
    # 데모: 외부 호출 대신 승인된 것으로 가정
    return {"authorized": True, "amount": amount}
