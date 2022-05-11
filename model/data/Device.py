from typing import List


class Device:

    def __init__(self, name: str, tp, users_id: List[str], active):
        self.name = name
        self.tp = tp
        self.users_id = users_id
        self.active = active
