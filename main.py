import json
from typing import List

from pyrebase import pyrebase
from pyrebase.pyrebase import Firebase, PyreResponse
from telegram.ext import Updater

config_name, token = 'config.json', '5303647214:AAFfM1nxeSQw7z259f0Ka_KAUIm_mVpJyCo'


def get_config() -> str:
    with open(config_name, 'r') as config_file:
        return parse_from_file(config_file)


def parse_from_file(read_file) -> str:
    return json.load(read_file)


def establish_firebase():
    firebase_config = get_config()
    return pyrebase.initialize_app(firebase_config)


class User:

    def __init__(self, login: str):
        self.login = login


class Device:

    def __init__(self, name: str, users_id: List[str], active):
        self.name = name
        self.users_id = users_id
        self.active = active


class ObjectMapper:

    @staticmethod
    def parse_devices(response: PyreResponse) -> List[Device]:
        def parse_single(item: PyreResponse):
            return Device(item.val()['name'], item.val()['users_id'], item.val()['active'])

        map_query = map(parse_single, response.each())
        return list(map_query)

    @staticmethod
    def parse_users(response: PyreResponse) -> List[User]:
        def parse_single(item: PyreResponse):
            return User(item.val()['login'])

        map_query = map(parse_single, response.each())
        return list(map_query)


class UserDao:

    def __init__(self, firebase: Firebase):
        self.db = firebase.database()

    def get_all(self):
        users = self.db.child("users").get()
        return ObjectMapper.parse_users(users) if users.each() is not None else []

    def insert(self, user: User):
        user_dict = user.__dict__
        self.db.child("users").push(user_dict)


class DeviceDao:

    def __init__(self, firebase: Firebase):
        self.db = firebase.database()

    def get_all(self):
        devices = self.db.child("devices").get()
        return ObjectMapper.parse_devices(devices) if devices.each() is not None else []

    def get_by_user(self, user: User):
        return [d for d in self.get_all() if user.login in d.users_id]

    def insert(self, device: Device):
        device_dict = device.__dict__
        self.db.child("devices").push(device_dict)


def main():
    firebase = establish_firebase()
    dev_dao = DeviceDao(firebase)
    usr_dao = UserDao(firebase)

    updater = Updater(token)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
