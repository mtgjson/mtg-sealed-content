import json
import itertools as itr


class card:
    def __init__(self, contents):
        self.name = contents["name"]
        self.set = contents["set"]
        self.number = contents["number"]
        self.etched = contents.get("etched", False)
        self.foil = contents.get("foil", False)
        self.uuid = contents.get("uuid", False)

    def toJson(self):
        data = {"name": self.name, "set": self.set, "number": str(self.number)}
        if self.uuid:
            data["uuid"] = self.uuid
        if self.foil:
            data["foil"] = self.foil
        if self.etched:
            data["etched"] = self.etched
        return data

    def get_uuids(self, uuid_map):
        try:
            self.uuid = uuid_map[self.set.lower()]["cards"][str(self.number)][0]
            if self.name not in uuid_map[self.set.lower()]["cards"][str(self.number)][1]:
                raise ValueError("name and number do not match", self.name, self.name)
        except KeyError:
            with open("status.txt", "a") as f:
                f.write(f"Card number {self.set}:{self.number} not found in set {self.set}\n")
            self.uuid = None
        except ValueError:
            with open("status.txt", "a") as f:
                f.write(f"Card number {self.set}:{self.number} not found with name {self.name}\n")
            self.uuid = None


class pack:
    def __init__(self, contents):
        self.set = contents["set"]
        self.code = contents["code"]

    def toJson(self):
        data = {"set": self.set, "code": self.code}
        return data

    def get_uuids(self, uuid_map):
        try: 
            umap = uuid_map[self.set.lower()]["booster"]
        except KeyError:
            umap = False
            with open("status.txt", "a") as f:
                f.write(f"Booster code {self.code} not found in set {self.set}\n")
        if umap and self.code not in umap:
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
        try:
            umap = uuid_map[self.set.lower()]["decks"]
        except KeyError:
            umap = False
            with open("status.txt", "a") as f:
                f.write(f"Deck named {self.name} not found in set {self.set}\n")
        if umap and self.name not in umap:
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
            self.uuid = uuid_map[self.set.lower()]["sealedProduct"][self.name]
        except KeyError:
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
            if s['name'] == self.name:
                raise ValueError(f"Self-referrential product {self.name}")
            self.sealed.append(sealed(s))
        self.other = []
        for o in contents.get("other", []):
            self.other.append(other(o))
        self.chance = contents.get("chance", 1)
        self.weight = contents.get("weight", 0)

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
            if "weight" in options:
                if sum(v.chance for v in self.variable) != options['weight']:
                    raise ValueError(f"Weight incorrectly assigned for product {self.name}")
            else:
                options["weight"] = sum(v.chance for v in self.variable)
            for v in self.variable:
                v.weight = options["weight"]
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
        self.chance *= target.chance

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
        if self.weight:
            data["variable_config"] = [{"chance": self.chance, "weight": self.weight}]
        return data

    def get_uuids(self, uuid_map):
        if self.name:
            try:
                self.uuid = uuid_map[self.set_code.lower()]["sealedProduct"][self.name]
            except KeyError:
                with open("status.txt", "a") as f:
                    f.write(
                        f"Product name {self.name} not found in set {self.set_code}\n"
                    )
                self.uuid = None
        else:
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
