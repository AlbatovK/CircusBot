from typing import List

from pyrebase.pyrebase import PyreResponse

from model.data.Device import Device
from model.data.Root import Root
from model.data.User import User


class ObjectMapper:

    @staticmethod
    def parse_devices(response: PyreResponse) -> List[Device]:

        def parse_single(item: PyreResponse) -> Device:
            return Device(item.val()['name'], item.val()['tp'], item.val()['users_id'], item.val()['active'])

        map_query = map(parse_single, response.each())
        return list(map_query)

    @staticmethod
    def parse_users(response: PyreResponse) -> List[User]:

        def parse_single(item: PyreResponse) -> User:
            return User(item.val()['login'])

        map_query = map(parse_single, response.each())
        return list(map_query)

    @staticmethod
    def parse_roots(response: PyreResponse) -> List[Root]:

        def parse_single(item: PyreResponse) -> Root:
            return Root(item.val()['name'], item.val()['actions'])

        map_query = map(parse_single, response.each())
        return list(map_query)
