from mtg_sealed_choices.model import Card, Deck, Other, Pack, Product, Sealed


class card(Card):
    def get_uuids(self, uuid_map):
        try:
            set_map = uuid_map[self.set.lower()]
            number = str(self.number)
            # Tokens (e.g. SLD 918 "Food") live in a separate map from the
            # regular cards, and the token flag picks which one to look in.
            primary = "tokens" if self.token else "cards"
            fallback = "cards" if self.token else "tokens"
            if number in set_map[primary]:
                entry = set_map[primary][number]
            else:
                # Still resolve it, but report the mismatch so the flag can be
                # corrected in the YAML.
                entry = set_map[fallback][number]
                with open("status.txt", "a") as f:
                    f.write(
                        f"Card number {self.set}:{self.number} found in {fallback}, "
                        f"token flag should be {not self.token}\n"
                    )
            self.uuid = entry[0]
            if self.name not in entry[1]:
                raise ValueError("name and number do not match", self.name, self.name)
        except KeyError:
            with open("status.txt", "a") as f:
                f.write(f"Card number {self.set}:{self.number} not found in set {self.set}\n")
            self.uuid = None
        except ValueError:
            with open("status.txt", "a") as f:
                f.write(f"Card number {self.set}:{self.number} not found with name {self.name}\n")
            self.uuid = None


class pack(Pack):
    def get_uuids(self, uuid_map):
        try: 
            umap = uuid_map[self.set.lower()]["booster"]
        except KeyError:
            umap = False
        if not umap or (self.code not in umap):
            print(f"Booster code {self.code} not found in set {self.set}")
            with open("status.txt", "a") as f:
                f.write(f"Booster code {self.code} not found in set {self.set}\n")


class deck(Deck):
    def get_uuids(self, uuid_map):
        try:
            umap = uuid_map[self.set.lower()]["decks"]
        except KeyError:
            umap = False
        if not umap or (self.name not in umap):
            print(f"Deck named {self.name} not found in set {self.set}")
            with open("status.txt", "a") as f:
                f.write(f"Deck named {self.name} not found in set {self.set}\n")


class sealed(Sealed):
    def get_uuids(self, uuid_map):
        try:
            self.uuid = uuid_map[self.set.lower()]["sealedProduct"][self.name]
        except KeyError:
            with open("status.txt", "a") as f:
                f.write(f"Product name {self.name} not found in set {self.set}\n")
            self.uuid = None


class other(Other):
    pass


class product(Product):
    card_type = card
    pack_type = pack
    deck_type = deck
    sealed_type = sealed
    other_type = other

    def unknown_bonus(self):
        with open("status.txt", "a") as f:
            f.write(f"Product name {self.name} missing bonus card definition\n")

    def resolve_uuid(self, uuid_map):
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
