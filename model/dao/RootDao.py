from typing import List

from pyrebase.pyrebase import Firebase

from domain.ObjectWrapper import ObjectMapper
from model.data.Root import Root


class RootDao:

    def __init__(self, fb: Firebase):
        self.db = fb.database()

    def insert(self, root: Root):
        root_dict = root.__dict__
        self.db.child("device_root").child(root.name).set(root_dict)

    def get_all(self) -> List[Root]:
        roots = self.db.child("device_root").get()
        return ObjectMapper.parse_roots(roots) if roots.each() is not None else []

    def get_by_name(self, name: str):
        return [x for x in self.get_all() if x.name == name]
