import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        # Не сериализуем request, headers, body, исключение SQLAlchemy или repr модели.
        return json.dumps({
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
            **getattr(record, "fields", {}),
        }, ensure_ascii=False)


logger = logging.getLogger("lab4")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger.addHandler(handler)


def event(name: str, *, error: bool = False, **fields):
    logger.log(logging.ERROR if error else logging.INFO, name, extra={"fields": fields})
