import os
from flask import Flask, request, Response
import requests

app = Flask(__name__)

TOKEN = os.environ.get('STAYSEE_TOKEN', '')
STAYSEE = 'https://api.staysee.jp'

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
}

@app.route('/v1/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def proxy(path):
    if request.method == 'OPTIONS':
        return Response('', 200, CORS_HEADERS)

    url = f'{STAYSEE}/v1/{path}'
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
    }

    if request.method == 'POST':
        resp = requests.post(url, headers=headers, data=request.get_data(), params=request.args)
    else:
        resp = requests.get(url, headers=headers, params=request.args)

    response = Response(resp.content, resp.status_code)
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    response.headers['Content-Type'] = 'application/json'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
