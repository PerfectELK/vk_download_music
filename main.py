import vk_api
from vk_api.audio import VkAudio
from cryptography.fernet import Fernet
import requests
import os
from sanitize_filename import sanitize
import eyed3


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
        print('getting track: {0}'.format(music_list[i]['title']))
        put_music(music_list[i], r)
        i += 1
    print('music files is got')


def get_all_music(vk_audio, list_dirs):
    tracks = []
    print('Start getting music objects')
    # i = 0
    for track in vk_audio.get_iter():
        # if i == 1:
        #     break
        if str(track['id']) in list_dirs:
            print(track['title'] + ' already exist')
            continue
        print(track['title'] + ' put to array')
        tracks.append(track)
        # i += 1
    print('Music objects is got')
    return tracks


def put_music(music, response):
    path = './files/music/{0}'.format(music['id'])
    if not os.path.exists(path):
        os.makedirs(path)

    file_name = music['title']
    file_name = file_name.replace('/', '|')
    file_name = sanitize(file_name)
    file_path = '{0}/{1}.mp3'.format(path, file_name)
    file = open(file_path, 'wb')
    file.write(response.content)
    file.close()

    audio = eyed3.load(file_path)
    if audio.tag is None:
        audio.tag = eyed3.id3.Tag()
        audio.tag.file_info = eyed3.id3.FileInfo(file_path)
    artist = audio.tag.artist
    title = audio.tag.title

    if title is None:
        audio.tag.title = music['title']
    if artist is None:
        audio.tag.artist = music['artist']
    if len(music['track_covers']):
        curr_images = [y.description for y in audio.tag.images]
        for image in curr_images:
            audio.tag.images.remove(image)
        img_url = music['track_covers'][len(music['track_covers']) - 1]
        r = requests.get(img_url)
        audio.tag.images.set(3, r.content, 'image/jpeg')

    audio.tag.save(version=(2, 3, 0))
    track_name = '{0}-{1}-{2}.mp3'.format(audio.tag.artist, audio.tag.album if audio.tag.album is not None else '', audio.tag.title)
    track_name = track_name.replace('--', '-')
    track_name = sanitize(track_name)
    new_track_path = '{0}/{1}'.format(path, track_name)
    os.rename(file_path, new_track_path)


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