from fastapi import APIRouter

api_router = APIRouter()

# Imported after router creation to avoid circular imports.
# Each sub-module calls api_router.post / api_router.get etc.
from cascade_api.api import reprioritize as _reprioritize  # noqa: F401, E402
from cascade_api.api import steer as _steer  # noqa: F401, E402
from cascade_api.api import status as _status  # noqa: F401, E402
from cascade_api.api import plan as _plan  # noqa: F401, E402
from cascade_api.api import log as _log  # noqa: F401, E402
from cascade_api.api import review as _review  # noqa: F401, E402
from cascade_api.api import payment, stripe_webhook  # noqa: E402
from cascade_api.api import onboard  # noqa: E402
from cascade_api.api import cascade_plan  # noqa: E402
from cascade_api.api import cron  # noqa: E402
from cascade_api.api import telegram_webhook  # noqa: E402

api_router.include_router(payment.router)
api_router.include_router(stripe_webhook.router)
api_router.include_router(onboard.router)
api_router.include_router(cascade_plan.router)
api_router.include_router(cron.router)
api_router.include_router(telegram_webhook.router)
