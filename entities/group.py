# TODO add more fields
from typing import List


class Group:
    def __init__(self, cid, present_bots, language):
        self.cid: int = cid
        self.present_bots: List[int] = present_bots
        self.language = language

    def __iter__(self):
        yield "cid", self.cid
        yield "present_bots", self.present_bots
        yield "language", self.language

    @classmethod
    def from_json(cls, json):
        if not json:
            return None
        return cls(json["cid"], json["present_bots"], json["language"])
