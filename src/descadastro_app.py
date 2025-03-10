from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return 'API de descadastro está funcionando.'

@app.route('/descadastro')
def descadastro():
    return 'funcionou'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
