import unittest

from scripts.tokens.mtgjson_to_tcgplayer_mapper import MtgjsonToTcgplayerMapper


def soldier(uuid, number):
    return {"uuid": uuid, "name": "Soldier", "number": number, "layout": "token"}


PLAIN = soldier("plain", "2")
STAR = soldier("star", "2★")
FOIL = {"faceAttribute": ["Surge Foil"]}


class TokenMapperTests(unittest.TestCase):
    def map_face(self, face, tokens):
        faces = [{"faceName": "Soldier", "faceId": "2", "tokenType": "Token", **face}]
        MtgjsonToTcgplayerMapper().add_mtgjson_uuids_to_tcgplayer_token_face_details(
            "40K", {"T40K": tokens}, faces
        )
        return faces[0]["uuids"]

    def test_foil_face_prefers_the_star_printing(self):
        self.assertEqual(self.map_face(FOIL, [PLAIN, STAR]), ["star", "plain"])

    def test_plain_face_prefers_the_plain_printing(self):
        self.assertEqual(self.map_face({}, [PLAIN, STAR]), ["plain", "star"])

    def test_plain_face_prefers_the_plain_printing_listed_second(self):
        self.assertEqual(self.map_face({}, [STAR, PLAIN]), ["plain", "star"])

    def test_star_printings_keep_their_order(self):
        tokens = [PLAIN, soldier("star-a", "2★"), soldier("star-b", "2★")]
        self.assertEqual(self.map_face(FOIL, tokens), ["star-a", "star-b", "plain"])
