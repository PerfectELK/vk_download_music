import vk_api
from vk_api.audio import VkAudio
from cryptography.fernet import Fernet
import requests
from sanitize_filename import sanitize
from eyed3 import id3
import inquirer
import os
import shutil


USERS_FOLDER = './files/users'

def get_key(path):
    return open(path, 'rb').read()


def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)


def put_in_file(file, content, mode='w'):
    f = open(file, mode)
    f.write(content)
    f.close()


def encrypt(data, key=None):
    if data is None:
        raise ValueError('Data is empty')
    if key is None:
        f = Fernet(get_key())
    else:
        f = Fernet(key)
    encypted = f.encrypt(data)
    return encypted


def decrypt(data, key=None):
    if data is None:
        raise ValueError('Data is empty')
    if key is None:
        f = Fernet(get_key())
    else:
        f = Fernet(key)
    decrypted_data = f.decrypt(data)
    return decrypted_data


def get(urls, music_list, music_folder=None):
    print('start getting music files')
    i = 0
    for url in urls:
        r = requests.get(url)
        print('getting track: {0}'.format(music_list[i]['title']))
        put_music(music_list[i], r, music_folder=music_folder, iter=i)
        i += 1
    print('music files is got')


def get_all_music(vk_audio, list_dirs):
    tracks = []
    print('Start getting music objects')
    #i = 0
    for track in vk_audio.get_iter():
        #if i == 50:
           #break
        if str(track['id']) in list_dirs:
            print(track['title'] + ' already exist')
            continue
        print(track['title'] + ' put to array')
        tracks.append(track)
        #i += 1
    print('Music objects is got')
    return tracks


def put_music(music, response, music_folder=None, iter=None):
    if (music_folder is None):
        path = './files/music/{0}'.format(music['id'])
    else:
        path ='{0}/{1}'.format(music_folder, music['id'])
    mkdir_if_not_exists(path)

    file_name = music['title']
    file_name = file_name.replace('/', '|')
    file_name = sanitize(file_name)
    file_path = '{0}/{1}.mp3'.format(path, file_name)
    file = open(file_path, 'wb')
    file.write(response.content)
    file.close()

    print(file_path)
    print(music['title'])

    tag = id3.Tag()
    tag.parse(file_path)
    try:
        tag.version = id3.ID3_DEFAULT_VERSION
    except:
        tag.version = id3.ID3_V1
    artist = tag.artist
    title = tag.title

    if title is None:
        tag.title = music['title']
    if artist is None:
        tag.artist = music['artist']
    if len(music['track_covers']):
        curr_images = [y.description for y in tag.images]
        for image in curr_images:
            tag.images.remove(image)
        img_url = music['track_covers'][len(music['track_covers']) - 1]
        r = requests.get(img_url)
        tag.images.set(3, r.content, 'image/jpeg')

    track_name = '{0}-{1}-{2}.mp3'.format(
        tag.artist, tag.album if tag.album is not None else '', tag.title
    )
    tag.title = track_name

    try:
        tag.save()
    except:
        tag.version = id3.ID3_V1
        tag.save()

    track_name = track_name.replace('--', '-')
    track_name = track_name.replace('--', '-')
    track_name = sanitize(track_name)

    new_track_path = '{0}/{1}'.format(path, track_name)
    os.rename(file_path, new_track_path)


def create_user():
    user_name = input('Enter user name:')
    user_phone = input('Enter user phone:')
    user_pass = input('Enter password:')

    vk_session = vk_api.VkApi(user_phone, user_pass)

    try:
        vk_session.auth()
    except:
        print('Invalid login or password')
        exit(0)

    user_dir = '{0}/{1}'.format(USERS_FOLDER, user_name)
    mkdir_if_not_exists(user_dir)

    key = Fernet.generate_key()
    put_in_file('{0}/{1}'.format(user_dir, 'crypto.key'), key, mode='wb')

    encrypted_phone = encrypt(bytes(user_phone, 'utf-8'), key=key)
    put_in_file('{0}/{1}'.format(user_dir, 'login.txt'), encrypted_phone, mode='wb')
    encrypted_pass = encrypt(bytes(user_pass, 'utf-8'), key=key)
    put_in_file('{0}/{1}'.format(user_dir, 'pass.txt'), encrypted_pass, mode='wb')
    return vk_session, user_name


if __name__ == '__main__':

    mkdir_if_not_exists(USERS_FOLDER)

    user_dirs = [d for d in os.listdir(USERS_FOLDER) if os.path.isdir(os.path.join(USERS_FOLDER, d))]
    user_dirs.append('+ New')

    questions = [inquirer.List('user', message="Wha-t user?", choices=user_dirs)]

    answers = inquirer.prompt(questions)

    vk_session = None
    user_name = None
    if answers['user'] == '+ New':
        vk_session, user_name = create_user()
    else:
        user_name = answers['user']
        key = open('{0}/{1}/{2}'.format(USERS_FOLDER, user_name, 'crypto.key'), 'rb').read()
        vk_login = open('{0}/{1}/{2}'.format(USERS_FOLDER, user_name, 'login.txt'), 'rb').read()
        vk_path = open('{0}/{1}/{2}'.format(USERS_FOLDER, user_name, 'pass.txt'), 'rb').read()
        decrypted_login = decrypt(vk_login, key=key).decode('utf-8')
        decrypt_pass = decrypt(vk_path, key=key).decode('utf-8')
        vk_session = vk_api.VkApi(decrypted_login, decrypt_pass)
        vk_session.auth()

    music_folder = '{0}/{1}/{2}'.format(USERS_FOLDER, user_name, 'music')

    questions = [inquirer.List('delete_music', message="Delete current music?", choices=['Yes', 'No'])]
    answers = inquirer.prompt(questions)
    if answers['delete_music'] == 'Yes':
        for root, dirs, files in os.walk(music_folder):
            for f in files:
                os.unlink(os.path.join(root, f))
            for d in dirs:
                shutil.rmtree(os.path.join(root, d))

    mkdir_if_not_exists(music_folder)
    list_dirs = [d for d in os.listdir(music_folder) if os.path.isdir(os.path.join(music_folder, d))]
    vk_audio = VkAudio(vk_session)
    music_list = get_all_music(vk_audio, list_dirs)
    urls = [music['url'] for music in music_list]
    if not len(urls):
        print('All music is sync')
        exit(1)
    get(urls, music_list, music_folder=music_folder)