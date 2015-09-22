from flask import Flask, session, redirect, url_for, escape, request
import json

app = Flask(__name__)

@app.route('/last')
def last():
    return "last"

@app.route('/sleep/<t>')
def sleep(t):
    import time
    time.sleep(int(t))
    return "sleeped - %s" % t


@app.route('/')
def index():
    if 'username' in session:
        return 'Logged in as %s' % escape(session['username'])
    return 'You are not logged in'

@app.route('/test-json')
def test_json():
    return json.dumps({'objects':[{'name': 'testfoo'}]})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return '''
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=submit value=Login>
        </form>
    '''

@app.route('/logout')
def logout():
    # remove the username from the session if it's there
    session.pop('username', None)
    return redirect(url_for('index'))

# set the secret key.  keep this really secret:
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

if __name__ == "__main__":
    app.run()