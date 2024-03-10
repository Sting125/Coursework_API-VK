import time
import requests
import os
import sys
import json
from pprint import pprint
import pyprind
from my_log import make_log

class YaUploader:
    host = 'https://cloud-api.yandex.net'  # Устанавливаем базовый URL для API Яндекс.Диска

    def __init__(self, token: str, log_path: str):
        self.token = token  # Сохраняем токен для аутентификации в API Яндекс.Диска
        self.log_path = log_path  # Сохраняем путь к файлу лога
        self.headers = {'Content-Type': 'application/json',
                        'Authorization': f'OAuth {self.token}'
                        }

    def create_folder(self): #Модуль дя создании папки на Яндекс.Диске
        url = f'{self.host}/v1/disk/resources'  # Формируем URL для создания папки на Яндекс.Диске
        params = {'path': 'VK', 'overwrite': True}  # Указываем параметры запроса (путь и флаг перезаписи)
        response = requests.put(url, params=params, headers=self.headers).json()  # Отправляем запрос на создание папки
        # pprint(response)

    def sent_file(self, file_name, url_photo):
        # Получим фото на диск
        with open(f'{file_name}.jpg', 'wb') as file:
            img = requests.get(url_photo)
            file.write(img.content)

        # Получаем ссылку, куда загружать
        url = f'{self.host}/v1/disk/resources/upload'
        params = {'path': 'VK/' + f'{file_name}.jpg', 'overwrite': True}
        resp = requests.get(url, params=params, headers=self.headers).json()
        print(resp)  # Выводим ответ на экран для отладки

        resp = resp.get('href')  # Получаем значение ключа 'href' без возможного KeyError

        # Загружаем на яндекс диск
        with open(f'{file_name}.jpg', 'rb') as file:
            response = requests.put(resp, data=file)

        # Удаляем локальные файлы с диска
        os.remove(f'{file_name}.jpg')

    @make_log('YaUploader.log')
    def upload_photos(self, photos_dict):
        # Создаём папку на Яндекс Диске
        self.create_folder()

        photos_log = []  # Список всех фото для лога
        # Пробегаемся по списку фото и загружаем на Яндекс Диск
        for likes, photos in photos_dict.items():
            # print(likes, photos)
            for photo in photos:
                photo_log = {}  # Инфа по 1 фото
                if len(photos) > 1:
                    file_name = str(likes) + ' ' + photo[0]
                else:
                    file_name = str(likes)
                # Загрузка на Яндекс Диск
                self.sent_file(file_name, photo[1])
                # Записываем инфу для лога
                photo_log['file_name'] = f'{file_name}.jpg'
                photo_log['size'] = 'z'
                photos_log.append(photo_log)
                bar.update()
        # Сохраняем лог
        with open(self.log_path, 'w') as log:  # Используем сохранённый путь к файлу лога
            json.dump(photos_log, log, indent=4)

class VKphotos:
    Url = 'https://api.vk.com/method/photos.get'

    def __init__(self, token: str, log_path: str):
        self.token = token
        self.log_path = log_path  # Сохраняем путь к файлу лога
        self.vk_id = int(input('Input ID: Введите ID номер: ') or '')  # Инициализируем vk_id (253710861)

    @make_log('VKphotos.log')
    def get_photos(self, count_photos):
        params = {
            'owner_id': self.vk_id,
            'access_token': self.token,
            'v': '5.131',
            'album_id': 'profile',
            'rev': 1,
            'extended': 1,
            'count': count_photos
        }
        try:
            # Получаем фото с ВК в словарь для дальнейшей загрузки
            photos = requests.get(self.Url, params=params).json()['response']['items']
        except KeyError:
            print("Error: Couldn't find 'response' key in the server's response.")
            return {}  # Возвращаем пустой словарь в случае ошибки

        photos_dict = {}
        i = 0
        for photo in photos:
            key = photo['likes']['count']
            sizes = photo['sizes']
            for size in sizes:
                if size['type'] == 'z':
                    url_photo = size['url']
                    break
            # Если такое количество лайков уже было, добавляем дату
            if key in photos_dict:
                photos_dict[key] = photos_dict[key] + [
                    [(time.strftime('%Y_%m_%d', time.gmtime(photo['date']))), url_photo]]
            else:
                photos_dict.setdefault(key, [[time.strftime('%Y_%m_%d', time.gmtime(photo['date'])), url_photo]])
            bar.update()
        return photos_dict

if __name__ == '__main__':
    # Получаем токен ВК
    with open('token_vk.txt', 'r') as file_token_vk:
        token_vk = file_token_vk.read().strip()
    # Получаем токен Яндекс Полигон
    with open('token_ya.txt', 'r') as file_token_ya:
        token_ya = file_token_ya.read().strip()

    count_photos = int(input('How many photos? (press enter for default = 5)') or 5)

    # Начинаем статус бар
    bar = pyprind.ProgBar(count_photos * 2, stream=sys.stdout)
    vk_photos = VKphotos(token_vk, 'VKphotos.log').get_photos(count_photos)
    ya_uploader = YaUploader(token_ya, 'YaUploader.log').upload_photos(vk_photos)