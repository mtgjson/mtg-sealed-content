import json
import itertools as itr


class card:
    def __init__(self, contents):
        self.name = contents["name"]
        self.set = contents["set"]
        self.number = contents["number"]
        self.foil = contents.get("foil", False)
        self.uuid = contents.get("uuid", False)

    def toJson(self):
        data = {"name": self.name, "set": self.set, "number": str(self.number)}
        if self.uuid:
            data["uuid"] = self.uuid
        if self.foil:
            data["foil"] = self.foil
        return data

    def get_uuids(self, uuid_map):
        try:
            self.uuid = uuid_map.get(self.set.lower(), {})["cards"][str(self.number)]
        except:
            with open("status.txt", "a") as f:
                f.write(f"Card number {self.number} not found in set {self.set}\n")
            self.uuid = None


class pack:
    def __init__(self, contents):
        self.set = contents["set"]
        self.code = contents["code"]

    def toJson(self):
        data = {"set": self.set, "code": self.code}
        return data

    def get_uuids(self, uuid_map):
        if self.code not in uuid_map.get(self.set.lower(), {})["booster"]:
            print(f"Booster code {self.code} not found in set {self.set}")
            with open("status.txt", "a") as f:
                f.write(f"Booster code {self.code} not found in set {self.set}\n")


class deck:
    def __init__(self, contents):
        self.set = contents["set"]
        self.name = contents["name"]

    def toJson(self):
        data = {"set": self.set, "name": self.name}
        return data

    def get_uuids(self, uuid_map):
        if self.name not in uuid_map.get(self.set.lower(), {}).get("decks"):
            print(f"Deck named {self.name} not found in set {self.set}")
            with open("status.txt", "a") as f:
                f.write(f"Deck named {self.name} not found in set {self.set}\n")


class sealed:
    def __init__(self, contents):
        self.set = contents["set"]
        self.count = contents["count"]
        self.name = contents["name"]
        self.uuid = contents.get("uuid", False)

    def toJson(self):
        data = {"set": self.set, "count": self.count, "name": self.name}
        if self.uuid:
            data["uuid"] = self.uuid
        return data

    def get_uuids(self, uuid_map):
        try:
            self.uuid = uuid_map.get(self.set.lower(), {})["sealedProduct"][self.name]
        except:
            with open("status.txt", "a") as f:
                f.write(f"Product name {self.name} not found in set {self.set}\n")
            self.uuid = None


class other:
    def __init__(self, contents):
        self.name = contents["name"]

    def toJson(self):
        data = {"name": self.name}
        return data


class product:
    def __init__(self, contents, set_code=None, name=None):
        self.name = name
        self.set_code = set_code
        if not contents:
            contents = {}
        self.card = []
        for c in contents.get("card", []):
            self.card.append(card(c))
        self.pack = []
        for p in contents.get("pack", []):
            self.pack.append(pack(p))
        self.deck = []
        for d in contents.get("deck", []):
            self.deck.append(deck(d))
        self.sealed = []
        for s in contents.get("sealed", []):
            self.sealed.append(sealed(s))
        self.other = []
        for o in contents.get("other", []):
            self.other.append(other(o))

        self.card_count = contents.get("card_count", 0)

        self.variable = []
        if "variable_mode" in contents:
            options = contents.pop("variable_mode")
            if options.get("replacement", False):
                for combo in itr.combinations_with_replacement(
                    contents["variable"], options.get("count", 1)
                ):
                    p_temp = product({})
                    for c in combo:
                        p_temp.merge(product(c))
                    self.variable.append(p_temp)
            else:
                for combo in itr.combinations(
                    contents["variable"], options.get("count", 1)
                ):
                    p_temp = product({})
                    for c in combo:
                        p_temp.merge(product(c))
                    self.variable.append(p_temp)
        elif "variable" in contents:
            self.variable = [product(p) for p in contents["variable"]]

    def merge(self, target):
        self.card += target.card
        self.pack += target.pack
        self.deck += target.deck
        self.sealed += target.sealed
        self.variable += target.variable
        self.card_count += target.card_count
        self.other += target.other

    def toJson(self):
        data = {}
        if self.card:
            data["card"] = [c.toJson() for c in self.card]
        if self.pack:
            data["pack"] = [p.toJson() for p in self.pack]
        if self.deck:
            data["deck"] = [d.toJson() for d in self.deck]
        if self.sealed:
            data["sealed"] = [s.toJson() for s in self.sealed]
        if self.other:
            data["other"] = [o.toJson() for o in self.other]
        if self.variable:
            data["variable"] = [{"configs": [v.toJson() for v in self.variable]}]
        if self.card_count:
            data["card_count"] = self.card_count
        return data

    def get_uuids(self, uuid_map):
        try:
            self.uuid = uuid_map[self.set_code.lower()]["sealedProduct"][self.name]
        except:
            if self.name:
                with open("status.txt", "a") as f:
                    f.write(
                        f"Product name {self.name} not found in set {self.set_code}\n"
                    )
            self.uuid = None
        for c in self.card:
            c.get_uuids(uuid_map)
        for p in self.pack:
            p.get_uuids(uuid_map)
        for d in self.deck:
            d.get_uuids(uuid_map)
        for s in self.sealed:
            s.get_uuids(uuid_map)
        for v in self.variable:
            v.get_uuids(uuid_map)
