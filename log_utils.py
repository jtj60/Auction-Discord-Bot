import datetime
import logging
import logging.config
import json
from collections import OrderedDict


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {"format": "%(message)s"},
    },
    "handlers": {
        "default": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",  # Default is stderr
        },
        "eventlog": {
            "level": "INFO",
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": "events.log",
        },
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["default"],
            "level": "WARNING",
            "propagate": False,
        },
        "events": {
            "handlers": ["default", "eventlog"],
            "level": "INFO",
            "propagate": False,
        },
        "transitions": {
            "handlers": ["default", "eventlog"],
            "level": "INFO",
            "propagate": False,
        },
        "__main__": {  # if __name__ == '__main__'
            "handlers": ["default"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

# Run once at startup:
logging.config.dictConfig(LOGGING_CONFIG)
command_log = logging.getLogger("events")

def log_command(ctx, message_body=None, **other_info):
    logging_payload = OrderedDict(
        timestamp=datetime.datetime.now().isoformat(),
        author=ctx.message.author.name,
        message=str(ctx.message.content),
    )

    logging_payload.update(other_info)
    command_log.info(json.dumps(logging_payload))

def log_state_transition(start_state, end_state, **message_info):
    logging_payload = OrderedDict(
        timestamp=datetime.datetime.now().isoformat(),
        start_state=start_state,
        end_state=end_state,
    )
    logging_payload.update(message_info)
    command_log.info(json.dumps(logging_payload))
