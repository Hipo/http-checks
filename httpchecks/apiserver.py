from flask import Flask, session, redirect, url_for, escape, request

app = Flask(__name__)
app.debug = True

@app.route('/main')
def main():
    return "hello"

@app.route('/last')
def last():
    return "last"

