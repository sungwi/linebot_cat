import json
import requests
import base64
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .api import (
    REPLY_ENDPOINT_URL,
    ACCESS_TOKEN,
    DEEPL_AUTH_KEY,
    DEEPL_API,
    GOOGLE_CLOUD_VISION_API,
)

@csrf_exempt
def linebot_webhook(request):
    """
    given request of Line image message, detect wheter it's cat or not and reply to user
    / Line画像メッセージのリクエストを取得し、猫かどうか判断して、ユーザーに返信する
    """
    if request.method == 'POST':
        req_body = json.loads(request.body.decode('utf-8'))
        print(req_body)
        # handle sent message request via Line / 送信されたメッセージリクエストの処理
        for event in req_body['events']:
            # let the sent message state be "read" / 送信されたメッセージを既読にする処理
            # if event.get('source', {}).get('type') == 'user' and 'userId' in event['source']:
            #     userId = event['source']['userId']
            #     markMessageAsRead(userId)
            # handle image message / 画像メッセージの処理
            if event.get('type') == 'message' and event.get('message', {}).get('type') == 'image':
                reply_token = event['replyToken']
                img_id = event['message']['id']
                handle_image_message(reply_token, img_id)
        return JsonResponse({'status': 'ok'}, status=200)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

def markMessageAsRead(userId):
    """
    法人手続き申請しないと使えない？
    """
    # api endpoint of markasread / 既読APIエンドポイント
    api_url = 'https://api.line.me/v2/bot/message/markAsRead'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {ACCESS_TOKEN}'}
    payload = {
        'chat': {
            'userId': userId
        }
    }
    response = requests.post(api_url, headers=headers, json=payload)
    if response.status_code == 200:
        print('success markAsRead API: marked message as Read')
    else:
        print(f'Fail markAsRead API: {response.status_code}, {response.text}')

def translate_text(text):
    """
    translate reply message from bot using Deepl API
    / ボットの返信メッセージをDeepl APIを使って、日本語訳する
    """
    headers = {'Content-Type': 'application/json', 'Authorization': f'DeepL-Auth-Key {DEEPL_AUTH_KEY}'}
    payload = {
        'text': [text],
        'source_lang': 'EN',
        'target_lang': 'JA'
    }
    response = requests.post(DEEPL_API, headers=headers, json=payload)
    if response.status_code == 200:
        response_data = response.json()
        print(response_data)
        translated = response_data.get('translations')[0].get('text')
        return translated
    return None


def handle_image_message(reply_token, img_id):
    """
    reply to user depending on the result of the detection of whether the image is of cat or not
    / 画像メッセージをGoogle Cloud Vision APIに送って、猫かどうか判断し、結果によって返信する
    """
    IMG_URL = f'https://api-data.line.me/v2/bot/message/{img_id}/content'
    headers = {'Authorization': f'Bearer {ACCESS_TOKEN}'}
    response = requests.get(IMG_URL, headers=headers)
    img_content = response.content

    is_cat, possibility_text = detect_cat(img_content)
    
    if is_cat:
        text = f'Meow, {possibility_text}'
        translated = translate_text(text)
        if translated:
            text += f' \ {translated}'
        reply_msg = {'type': 'text', 'text':text}
    else:
        text = f'Oops, it\'s not cat! {possibility_text}'
        translated = translate_text(text)
        if translated:
            text += f' \ {translated}'
        reply_msg = {'type': 'text', 'text': text}
    reply(reply_token, [reply_msg])

def detect_cat(img_content):
    """
    Detect if the image is of cat or not with Google Cloud Vision API
    / Google Cloud Vision APIによって、猫かどうか判断する
    """
    encoded_image = base64.b64encode(img_content).decode('utf-8')
    payload = {
        'requests': [{
            'image': {
                'content': encoded_image
            },
            'features': [{
                'type': 'LABEL_DETECTION',
                'maxResults': 10
            }]
        }]
    }

    response = requests.post(GOOGLE_CLOUD_VISION_API, json=payload)

    if response.status_code != 200:
        print(f'Error Code:{response.status_code}')
        print(response.text)
        return False
    
    response_data = response.json()
    if 'responses' not in response_data or not response_data['responses']:
        print('Invalid response data:', response_data)
        return False

    labels = response_data['responses'][0]['labelAnnotations']
    print(labels)
    for label in labels:
        if label['description'].lower() == 'cat':
            if label['score'] >= 0.9:
                text = 'Abusolutely!!'
            elif label['score'] >= 0.8:
                text = 'Certainly!'
            elif label['score'] >= 0.6:
                text = 'Probably'
            elif label['score'] >= 0.4:
                text = 'Maybe?'
            else:
                text = 'Possibly...'
            return True, text
    # if cat is not detected, return first three candidates
    # / もし猫でない場合3つ候補を返信する
    text = f"Is it among {labels[0]['description']}, {labels[1]['description']} or {labels[2]['description']}?"
    return False, text

def reply(reply_token, messages):
    """
    reply to user after image detection
    / 画像識別後に、トーク画面にメッセージを返信する
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + ACCESS_TOKEN
    }
    body = {
        'replyToken': reply_token,
        'messages': messages
    }
    requests.post(REPLY_ENDPOINT_URL, headers=headers, data=json.dumps(body))
