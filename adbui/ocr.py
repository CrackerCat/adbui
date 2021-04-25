# coding=utf-8
import logging
import os
import time
import random
import traceback

import requests
import json
import hmac, hashlib
import binascii
import base64


class Ocr(object):
    def __init__(self, keys):
        self.keys = keys
        self.app_id = None
        self.secret_id = None
        self.secret_key = None
        self.result = None
        os.environ['NO_PROXY'] = 'api.youtu.qq.com'  # 防止代理影响结果
        if len(keys) == 0:
            raise NameError('ocr appid or secret_id or secret_key is None')

    def __app_sign(self):
        now = int(time.time())
        expired = now + 2592000
        rdm = random.randint(0, 999999999)
        plain_text = 'a={}&k={}&e={}&t={}&r={}&u=xx&f='.format(self.app_id, self.secret_id, expired, now, rdm)
        b = hmac.new(self.secret_key.encode(), plain_text.encode(), hashlib.sha1)
        s = binascii.unhexlify(b.hexdigest()) + plain_text.encode('ascii')
        signature = base64.b64encode(s).rstrip()  # 生成签名
        return signature

    def __get_headers(self):
        sign = self.__app_sign()
        headers = {'Authorization': sign, 'Content-Type': 'text/json'}
        return headers

    def get_result_path(self, image_path):
        if len(image_path) == 0:
            return {'errormsg': 'IMAGE_PATH_EMPTY'}

        filepath = os.path.abspath(image_path)
        if not os.path.exists(filepath):
            return {'errormsg': 'IMAGE_FILE_NOT_EXISTS'}

        out = open(filepath, 'rb').read()
        return self.get_result(out)

    def get_result(self, image):
        self.result = None
        image = base64.b64encode(image)
        image = image.rstrip().decode('utf-8')

        for key in self.keys:  # 使用多个优图账号尝试,防止某个账号频率限制
            if 'extended' not in key:
                key['extended'] = 0  # 初始化碰到限制的次数
            if key['extended'] > 3:
                continue  # 经常遇到频率限制的账号不用了
            self.app_id = key['app_id']
            self.secret_id = key['secret_id']
            self.secret_key = key['secret_key']
            headers = self.__get_headers()
            url = 'http://api.youtu.qq.com/youtu/ocrapi/generalocr'
            data = {"app_id": key['app_id'], "session_id": '', "image": image}

            try:
                r = requests.post(url, headers=headers, data=json.dumps(data))
                if r.status_code == 200:
                    r.encoding = 'utf-8'
                    self.result = r.json()
                    break
                else:
                    if r.status_code == 510:
                        key['extended'] = key['extended'] + 1
                    logging.error('ocr请求返回异常:code {}, app_id {}'.format(r.status_code, key['app_id']))
            except Exception as e:
                traceback.print_exc()

        if self.result and 'items' in self.result:
            return self.result
        else:
            logging.info('result:{}'.format(self.result))
            raise NameError('OCR 请求异常')


