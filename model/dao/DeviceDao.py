from pyrebase.pyrebase import Firebase

from domain.ObjectWrapper import ObjectMapper
from model.data.Device import Device
from model.data.User import User


class DeviceDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def update_device_status(self, device: Device, active: bool):
        update_dict = {"active": True if active else False}
        self.db.child("devices").child(device.name).update(update_dict)

    def get_all(self):
        devices = self.db.child("devices").get()
        return ObjectMapper.parse_devices(devices) if devices.each() is not None else []

    def get_by_user(self, usr: User):
        return [d for d in self.get_all() if usr.login in d.users_id]

    def insert(self, device: Device):
        device_dict = device.__dict__
        self.db.child("devices").child(device.name).set(device_dict)
