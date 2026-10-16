import unittest

from scripts.tokens.mtgjson_to_tcgplayer_mapper import MtgjsonToTcgplayerMapper


def soldier(uuid, number):
    return {"uuid": uuid, "name": "Soldier", "number": number, "layout": "token"}


class TokenMapperTests(unittest.TestCase):
    def map_face(self, face):
        faces = [{"faceName": "Soldier", "faceId": "2", "tokenType": "Token", **face}]
        MtgjsonToTcgplayerMapper().add_mtgjson_uuids_to_tcgplayer_token_face_details(
            "40K", {"T40K": [soldier("plain", "2"), soldier("star", "2★")]}, faces
        )
        return faces[0]["uuids"]

    def test_foil_face_prefers_the_star_printing(self):
        self.assertEqual(self.map_face({"faceAttribute": ["Surge Foil"]}), ["star", "plain"])

    def test_plain_face_prefers_the_plain_printing(self):
        self.assertEqual(self.map_face({}), ["plain", "star"])
