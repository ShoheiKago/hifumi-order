import os
import json
import hmac
import hashlib
import base64
import time
import uuid
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

STAYSEE_TOKEN = os.environ.get('STAYSEE_TOKEN', '')
LINE_TOKEN = os.environ.get('LINE_TOKEN', '')
LINE_GROUP_ID = os.environ.get('LINE_GROUP_ID', '')
STAYSEE_BASE = 'https://api.staysee.jp/v1'

# ===== Staysee プロキシ =====
@app.route('/staysee/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def staysee_proxy(path):
    url = f"{STAYSEE_BASE}/{path}"
    headers = {
        'Authorization': f'Bearer {STAYSEE_TOKEN}',
        'Content-Type': 'application/json'
    }
    try:
        if request.method == 'GET':
            r = requests.get(url, headers=headers, params=request.args)
        else:
            r = requests.request(request.method, url, headers=headers, json=request.get_json())
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== LINE 通知 =====
@app.route('/notify', methods=['POST'])
def notify():
    data = request.get_json()
    room = data.get('room', '')
    guest = data.get('guest', '')
    items = data.get('items', [])
    total = data.get('total', 0)
    note = data.get('note', '')

    items_text = ', '.join([i['name'] + '×' + str(i['qty']) for i in items])
    msg = '【飲料注文】\n部屋：' + room + '\n宿泊者：' + guest + ' 様'
    if items:
        msg += '\n注文：' + items_text + '\n合計：¥' + f'{total:,}'
    if note:
        msg += '\n📝 追記：' + note

    try:
        requests.post(
            'https://api.line.me/v2/bot/message/push',
            headers={
                'Authorization': f'Bearer {LINE_TOKEN}',
                'Content-Type': 'application/json'
            },
            json={
                'to': LINE_GROUP_ID,
                'messages': [{'type': 'text', 'text': msg}]
            }
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== LINE Webhook =====
@app.route('/webhook', methods=['POST'])
def webhook():
    return jsonify({'status': 'ok'})

# ===== SwitchBot ヘッダー生成 =====
def switchbot_headers(token, secret):
    t = str(int(round(time.time() * 1000)))
    nonce = str(uuid.uuid4())
    msg = token + t + nonce
    sign = base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), digestmod=hashlib.sha256).digest()
    ).decode()
    return {
        'Authorization': token,
        'sign': sign,
        't': t,
        'nonce': nonce,
        'Content-Type': 'application/json'
    }

# ===== SwitchBot デバイス一覧 =====
@app.route('/switchbot/devices', methods=['POST'])
def switchbot_devices():
    data = request.get_json()
    token = data.get('token', '')
    secret = data.get('secret', '')
    if not token or not secret:
        return jsonify({'error': 'token and secret required'}), 400
    try:
        r = requests.get(
            'https://api.switch-bot.com/v1.1/devices',
            headers=switchbot_headers(token, secret)
        )
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== SwitchBot デバイスステータス =====
@app.route('/switchbot/device-status', methods=['POST'])
def switchbot_device_status():
    data = request.get_json()
    token = data.get('token', '')
    secret = data.get('secret', '')
    device_id = data.get('deviceId', '')
    if not token or not secret or not device_id:
        return jsonify({'error': 'token, secret, deviceId required'}), 400
    try:
        r = requests.get(
            f'https://api.switch-bot.com/v1.1/devices/{device_id}/status',
            headers=switchbot_headers(token, secret)
        )
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== SwitchBot Webhook設定 =====
@app.route('/switchbot/webhook/setup', methods=['POST'])
def switchbot_webhook_setup():
    data = request.get_json()
    token = data.get('token', '')
    secret = data.get('secret', '')
    webhook_url = data.get('url', '')
    if not token or not secret or not webhook_url:
        return jsonify({'error': 'token, secret, url required'}), 400
    try:
        r = requests.post(
            'https://api.switch-bot.com/v1.1/webhook/setupWebhook',
            headers=switchbot_headers(token, secret),
            json={'action': 'setupWebhook', 'url': webhook_url, 'deviceList': 'ALL'}
        )
        return jsonify(r.json()), r.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== SwitchBot Webhook 状態保持 =====
# deviceId -> 最終検知タイムスタンプ（ミリ秒）
detection_state = {}

@app.route('/switchbot/webhook/receive', methods=['POST'])
def switchbot_webhook_receive():
    payload = request.get_json()
    print('SwitchBot Webhook:', json.dumps(payload))
    try:
        # SwitchBot Webhookのフォーマット: context.deviceMac or deviceId
        context = payload.get('context', {})
        device_id = context.get('deviceMac') or context.get('deviceId', '')
        event_type = context.get('eventType', '')
        # 動体検知イベント: WoPresence または motion系
        if device_id and ('motion' in event_type.lower() or 'detected' in event_type.lower() or context.get('moveDetected') or context.get('detectionState') == 'DETECTED'):
            detection_state[device_id] = int(time.time() * 1000)
            print(f'Motion detected: {device_id} at {detection_state[device_id]}')
    except Exception as e:
        print('Webhook parse error:', e)
    return jsonify({'status': 'ok'})

@app.route('/switchbot/webhook/status', methods=['GET'])
def switchbot_webhook_status():
    return jsonify({'detections': detection_state})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
