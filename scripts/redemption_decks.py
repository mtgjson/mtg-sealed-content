import ijson
import requests
import string

def get_decks(setup=""):
    if not setup:
        url = "https://mtgjson.com/api/v5/AllPrintings.json"
        r = requests.get(url, stream=True)
        parser = ijson.parse(r.content)
    else:
        ifile = open(setup, 'r')
        parser = ijson.parse(ifile)
    
    decks = {}
    current_set = ""
    status = ""
    ccode = ""
    name = ""
    dtype = ""
    size = 0
    for prefix, event, value in parser:
        if prefix == "data" and event == "map_key":
            current_set = value
            ccode = current_set.lower()
            decks[ccode] = {}
            status = ""
        elif prefix == f"data.{current_set}" and event == "map_key":
            status = value
        elif status == "decks":
            #print(prefix, event, value)
            if prefix == f"data.{current_set}.decks.item" and event == "end_map":
                decks[ccode][name] = (dtype, size)
                name = ""
                dtype = ""
                size = 0
            elif prefix == f"data.{current_set}.decks.item.name":
                name = value
            elif prefix == f"data.{current_set}.decks.item.type":
                dtype = value
            elif "count" in prefix and event=="number":
                size += value
    
    try:
        ifile.close()
    except:
        pass

    return decks

if __name__ == "__main__":
    decks = get_decks(r"/Users/samzimmerman/Downloads/AllPrintings.json")
    print(decks)
    for set_code, decknames in decks.items():
        redemption = [(k, v[1]) for k, v in decknames.items() if v[0] == 'MTGO Redemption']
        if redemption:
            if set_code == "con":
                set_upper = "CON_"
            else:
                set_upper = set_code.upper()
            with open(rf'/Users/samzimmerman/Source/mtg-sealed-content/data/products/{set_upper}.yaml', 'a') as prod_file:
                for p, _ in redemption:
                    if "Foil" in p:
                        p_clean = p[:-15].translate(str.maketrans('', '', string.punctuation))+"MTGO Redemption Foil"
                    else:
                        p_clean = p[:-10].translate(str.maketrans('', '', string.punctuation))+"MTGO Redemption"
                    prod_file.write(f"""  {p_clean}:
    category: BOX_SET
    identifiers: {{}}
    subtype: REDEMPTION
""")
            with open(rf'/Users/samzimmerman/Source/mtg-sealed-content/data/contents/{set_upper}.yaml', 'a') as cont_file:
                for p, s in redemption:
                    if "Foil" in p:
                        p_clean = p[:-15].translate(str.maketrans('', '', string.punctuation))+"MTGO Redemption Foil"
                    else:
                        p_clean = p[:-10].translate(str.maketrans('', '', string.punctuation))+"MTGO Redemption"
                    cont_file.write(f"""  {p_clean}:
    card_count: {s}
    deck:
    - name: "{p}"
      set: {set_code}
""")