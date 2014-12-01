from flask import Flask, session, redirect, url_for, escape, request
import json
import uuid
from sessioned_check import SessionedChecks
from httpcheck import get_request

app = Flask(__name__)
app.debug = True

checks = {}

@app.route('/hello')
def hello():
    return json.dumps({'result': True})

def finished(*args):
    print "finished....", args

@app.route('/check', methods=['POST'])
def check():
    id = uuid.uuid4()
    checks[id] = request.json
    print request.json

    k, conf = checks[id].items()[0]

    if isinstance(conf, list):
        sc = SessionedChecks(name=k, finish_callback=finished)
        for c in conf:
            # but individual urls in session must run in sync.
            r = get_request(k, c, session=sc.session)
            sc.add(r)
        # sync_map.append(sc)
    else:
        sc = SessionedChecks(name=k, finish_callback=finished)
        r = get_request(k,
                        conf,
                        session=sc.session)
        sc.add(r)
        sc.run()

    return json.dumps({'result': {'id': str(id)} })