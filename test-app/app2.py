from flask import Flask, session, redirect, url_for, escape, request

app = Flask(__name__)

@app.route('/last')
def last():
    return "last"

@app.route('/sleep/<t>')
def index(t):
    import time
    time.sleep(int(t))
    if 'username' in session:
        return 'Logged in as %s' % escape(session['username'])
    return 'You are not logged in'

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


import os

if __name__ == "__main__":
    app.run(port=int(os.environ.get('port', 5001)), debug=True)