import vk_api
from vk_api.audio import VkAudio
from cryptography.fernet import Fernet
import requests
import os
from sanitize_filename import sanitize

KEY_PATH = 'files/crypto.key'
LOGIN_PATH = 'files/login.txt'
PASS_PATH = 'files/pass.txt'

MUSIC_FOLDER = './files/music'

def get_key():
    return open(KEY_PATH, 'rb').read()


def encrypt(data):
    if data is None:
        raise ValueError('Data is empty')
    f = Fernet(get_key())
    encypted = f.encrypt(data)
    return encypted


def decrypt(data):
    if data is None:
        raise ValueError('Data is empty')
    f = Fernet(get_key())
    decrypted_data = f.decrypt(data)
    return decrypted_data


def get(urls, music_list):
    print('start getting music files')
    i = 0
    for url in urls:
        r = requests.get(url)
        put_music(music_list[i], r)
        i += 1
    print('music files is got')


def get_all_music(vk_audio, list_dirs):
    tracks = []
    print('Start getting music objects')
    for track in vk_audio.get_iter():
        if str(track['id']) in list_dirs:
            print(track['title'] + ' already exist')
            continue
        print(track['title'] + ' put to array')
        tracks.append(track)
    print('Music objects is got')
    return tracks


def put_music(music, response):
    path = './files/music/{0}'.format(music['id'])
    if not os.path.exists(path):
        os.makedirs(path)
    file_name = music['title']
    file_name = file_name.replace('/', '|')
    file_name = sanitize(file_name)
    file = open('{0}/{1}.mp3'.format(path, file_name), 'wb')
    file.write(response.content)
    file.close()


if __name__ == '__main__':
    VK_LOGIN = decrypt(open(LOGIN_PATH, 'rb').read()).decode("utf-8")
    VK_PASS = decrypt(open(PASS_PATH, 'rb').read()).decode("utf-8")
    vk_session = vk_api.VkApi(VK_LOGIN, VK_PASS)
    vk_session.auth()

    list_dirs = [d for d in os.listdir(MUSIC_FOLDER) if os.path.isdir(os.path.join(MUSIC_FOLDER, d))]
    vk_audio = VkAudio(vk_session)
    music_list = get_all_music(vk_audio, list_dirs)

    urls = [music['url'] for music in music_list]
    if not len(urls):
        print('All music is sync')
        exit(1)
    get(urls, music_list)