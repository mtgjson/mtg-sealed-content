import json
import itertools as itr

class card():
    def __init__(self, contents):
        self.name = contents["name"]
        self.set = contents["set"]
        self.number = contents["number"]
        self.foil = contents.get("foil", False)
        self.uuid = contents.get("uuid", False)
    
    def toJson(self):
        data = {
            "name": self.name,
            "set": self.set,
            "number": self.number
        }
        if self.uuid:
            data["uuid"] = self.uuid
        if self.foil:
            data["foil"] = self.foil
        return data


class pack():
    def __init__(self, contents):
        self.set = contents["set"]
        self.code = contents["code"]
    
    def toJson(self):
        data = {
            "set": self.set,
            "code": self.code
        }
        return data


class deck():
    def __init__(self, contents):
        self.set = contents["set"]
        self.name = contents["name"]
    
    def toJson(self):
        data = {
            "set": self.set,
            "name": self.name
        }
        return data


class sealed():
    def __init__(self, contents):
        self.set = contents["set"]
        self.count = contents["count"]
        self.name = contents["name"]
        self.uuid = contents.get("uuid", False)
    
    def toJson(self):
        data = {
            "set": self.set,
            "count": self.count,
            "name": self.name
        }
        if self.uuid:
            data["uuid"] = self.uuid
        return data


class other():
    def __init__(self, contents):
        self.name = contents["name"]
    
    def toJson(self):
        data = {
            "name": self.name
        }
        return data


class product():
    def __init__(self, contents):
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
                for combo in itr.combinations(contents["variable"], options.get("count", 1)):
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
            data["variable"] = [{"configs":[v.toJson() for v in self.variable]}]
        if self.card_count:
            data["card_count"] = self.card_count
        return data
