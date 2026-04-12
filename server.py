import os, json
from flask import Flask, request, Response
import requests

app = Flask(__name__)

STAYSEE_TOKEN = os.environ.get('STAYSEE_TOKEN', '')
LINE_TOKEN    = os.environ.get('LINE_TOKEN', '')
LINE_GROUP_ID = os.environ.get('LINE_GROUP_ID', '')
STAYSEE       = 'https://api.staysee.jp'

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
}

# ===== Staysee プロキシ =====
@app.route('/v1/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def proxy(path):
    if request.method == 'OPTIONS':
        return Response('', 200, CORS_HEADERS)

    url = f'{STAYSEE}/v1/{path}'
    headers = {
        'Authorization': f'Bearer {STAYSEE_TOKEN}',
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

# ===== LINE通知送信 =====
def send_line(message):
    if not LINE_TOKEN or not LINE_GROUP_ID:
        return
    requests.post(
        'https://api.line.me/v2/bot/message/push',
        headers={
            'Authorization': f'Bearer {LINE_TOKEN}',
            'Content-Type': 'application/json',
        },
        json={
            'to': LINE_GROUP_ID,
            'messages': [{'type': 'text', 'text': message}]
        }
    )

@app.route('/notify', methods=['POST', 'OPTIONS'])
def notify():
    if request.method == 'OPTIONS':
        return Response('', 200, CORS_HEADERS)

    data = request.get_json()
    room     = data.get('room', '')
    guest    = data.get('guest', '')
    items    = data.get('items', [])
    total    = data.get('total', 0)
    note     = data.get('note', '')

    items_str = '　'.join([f"{i['name']}×{i['qty']}" for i in items])
    msg = f"【飲料注文】\n部屋：{room}\n宿泊者：{guest} 様\n注文：{items_str}\n合計：¥{total:,}"
    if note:
        msg += f"\n📝 追記：{note}"

    send_line(msg)

    response = Response(json.dumps({'ok': True}), 200)
    for k, v in CORS_HEADERS.items():
        response.headers[k] = v
    response.headers['Content-Type'] = 'application/json'
    return response

# ===== LINE Webhook（グループID取得用）=====
@app.route('/webhook', methods=['POST'])
def webhook():
    body = request.get_json()
    for event in body.get('events', []):
        source = event.get('source', {})
        if source.get('type') == 'group':
            group_id = source.get('groupId', '')
            print(f'GROUP_ID: {group_id}')
    return Response('OK', 200)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8765))
    app.run(host='0.0.0.0', port=port)
