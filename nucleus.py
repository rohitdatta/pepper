from flask import Flask

app = Flask(__name__)


@app.route('/')
def nucleus():
    return 'Nucleus Home'


if __name__ == '__main__':
    app.run()
