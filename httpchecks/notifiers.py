try:
    import gevent
    from gevent import monkey as gmonkey
    from gevent.pool import Pool
except ImportError:
    raise RuntimeError('Gevent is required.')

import logging
import json
import requests

log = logging.getLogger(__name__)

def notify_by_slack(url, channel, username, description, icon_emoji):
    payload = {"channel": channel,
               "username": username,
               "text": str(description),
               "icon_emoji": icon_emoji}

    requests.post(url, dict(
        payload=json.dumps(payload)
    ))
