from flask import Flask, session, redirect, url_for, escape, request
import json
import uuid
import requests
from sessioned_check import SessionedChecks
from httpcheck import get_request

import logging
log = logging.getLogger(__name__)

app = Flask(__name__)
app.debug = True

checks = {}

@app.route('/hello')
def hello():
    return json.dumps({'result': True})


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def finished(result, req):
    print "finished....", result, req
    if req.options.get('callback_url', None):
        print "sending result to callback url", req.options['callback_url']
        try:

            steps = []
            for i in req.steps:
                print "------->>>>>", i, i.url, i.started_at, i.finished_at, i.response.status_code
                steps.append(dict(
                    url=i.url,
                    started_at = i.started_at,
                    finished_at = i.finished_at,
                    error = i.error,
                    status_code = i.response.status_code

                ))

            requests.post(
                req.options['callback_url'],
                headers={'content-type': 'application/json'},
                data=json.dumps(dict(
                    id=str(req.options['id']),
                    result=result,
                    finished_at = req.finished_at,
                    started_at = req.started_at,
                    steps = steps
                ), cls=DateEncoder)
            )
        except:
            log.exception('exception on passing callback url')
            raise

@app.route('/check', methods=['POST'])
def check():
    id = uuid.uuid4()
    checks[id] = request.json
    print request.json

    options = checks[id].pop('options', {})

    k, conf = checks[id].items()[0]

    options['id'] = id
    if isinstance(conf, list):
        sc = SessionedChecks(name=k,
                             finish_callback=finished,
                             options=options)
        for c in conf:
            # but individual urls in session must run in sync.
            r = get_request(k, c, session=sc.session)
            sc.add(r)
        sc.run()
    else:
        sc = SessionedChecks(name=k, finish_callback=finished, options=options)
        r = get_request(k,
                        conf,
                        session=sc.session)
        sc.add(r)
        sc.run()

    return json.dumps({'result': {'id': str(id)} })





