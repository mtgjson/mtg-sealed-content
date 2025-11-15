import json
import yaml
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional

from categorize import (
    ProductCategorizer,
    parse_item_number,
    categorize_with_hints
)

BATCH_SIZE = 10
REQUEST_TIMEOUT = 30
HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0'
}


def parse_date(date_str):
    """Parse MM/DD/YYYY date string to datetime object"""
    try:
        return datetime.strptime(date_str, "%m/%d/%Y")
    except Exception:
        return datetime.min


def extract_release_code(item_number: str) -> Optional[str]:
    """Extract release code after WCMG prefix"""
    match = re.match(r'WCMG([A-Z]{3})', item_number)
    return match.group(1) if match else None


def parse_product_configuration(config_text: str) -> Dict:
    """Parse product configuration text into structured data"""
    if not config_text:
        return {}
    
    parsed = {
        'raw': config_text,
        'components': []
    }
    
    case_match = re.search(r'(\d+)\s+(?:bundles?|boxes?|decks?|packs?)\s+per\s+case', config_text, re.IGNORECASE)
    if case_match:
        parsed['case_count'] = int(case_match.group(1))
    
    component_pattern = r'(\d+)\s+([^,.\d]+?)(?:,|\.|$)'
    for match in re.finditer(component_pattern, config_text):
        count = int(match.group(1))
        component = match.group(2).strip()
        if component and len(component) > 3:
            parsed['components'].append({
                'count': count,
                'item': component
            })
    
    return parsed


def scrape_product_listing(url):
    """Extract all products from the listing page"""
    print("Fetching listings...")
    
    response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, 'html.parser')
    rows = soup.find_all('tr', class_='productListing')
    
    if not rows:
        print("Error: No product listing rows found")
        return []
    
    products = []
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue
        
        name_cell = cells[1]
        link = name_cell.find('a')
        
        if not link:
            continue
        
        url_val = link.get('href', '')
        if url_val and not url_val.startswith('http'):
            url_val = 'https://www.southernhobby.com' + url_val if url_val.startswith('/') else url_val
        
        product = {
            'name': link.text.strip(),
            'url': url_val,
            'itemNumber': cells[2].text.strip(),
            'releaseDate': cells[3].text.strip()
        }
        
        products.append(product)
    
    print(f"Found {len(products)} products")
    return products


def scrape_product_details(url):
    """Extract product details from detail page"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        details = {}
        content_areas = soup.find_all('div', class_='subpage_content_border')
        
        for content in content_areas:
            main_div = content.find('div', class_='main')
            if main_div:
                bold = main_div.find('b')
                if bold:
                    config_text = bold.text.strip()
                    if 'configuration' in config_text.lower() or 'pack' in config_text.lower():
                        details['Product Configuration'] = config_text
            
            table = content.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td', class_='main')
                    if len(cells) == 2:
                        bold = cells[0].find('b')
                        if bold:
                            label = bold.text.strip()
                            value = cells[1].text.strip()
                            if label and value:
                                details[label] = value
        
        return details if details else None
        
    except Exception as e:
        print(f"  Error scraping details from {url}: {e}")
        return None


def process_product(product, index, total):
    """Process a single product"""
    item_number = product['itemNumber']
    details = scrape_product_details(product['url'])
    product_data = {
        'name': product['name'],
        'itemNumber': item_number,
        'releaseDate': product['releaseDate'],
        'url': product['url'],
        'details': details
    }
    
    return item_number, product_data


def main():
    """Main scraper function"""
    listing_url = "https://www.southernhobby.com/advanced_search_result.php?onpage=100&search_in_description=1&q=WCMG&keywords=WCMG"
    products = scrape_product_listing(listing_url)
    
    if not products:
        print("No products found. Exiting.")
        return
    
    all_data = {}
    
    with ThreadPoolExecutor(max_workers=BATCH_SIZE) as executor:
        futures = {
            executor.submit(process_product, product, i+1, len(products)): product
            for i, product in enumerate(products)
        }
        
        for future in as_completed(futures):
            try:
                item_number, product_data = future.result()
                all_data[item_number] = product_data
            except Exception as e:
                product = futures[future]
                print(f"Failed to process {product['itemNumber']}: {e}")

    sorted_data = dict(
        sorted(
            all_data.items(),
            key=lambda x: parse_date(x[1]['releaseDate']),
            reverse=True
        )
    )
    
    output_dir = Path('data')
    output_dir.mkdir(exist_ok=True)
    
    json_file = output_dir / 'soho.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(sorted_data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ JSON saved to {json_file}")
    generate_yaml_files(sorted_data, output_dir)


def generate_yaml_files(products: Dict, output_dir: Path):
    """Generate YAML files grouped by release code"""
    
    known_products = {}
    for item_number, data in products.items():
        category, subtype, confidence = categorize_with_hints(data['name'], item_number)
        if category != "UNKNOWN" and confidence >= 0.9:
            known_products[data['name']] = {
                'category': category,
                'subtype': subtype
            }

    ProductCategorizer.initialize_fuzzy(known_products)

    releases = defaultdict(dict)
    unknown_codes = []
    product_details = {}
    
    for item_number, data in products.items():
        release_code, language, _ = parse_item_number(item_number)
        
        if not release_code:
            unknown_codes.append(item_number)
            continue
        
        category, subtype, _ = categorize_with_hints(data['name'], item_number)
        
        product_entry = {
            'language': language,
            'category': category,
            'subtype': subtype,
            'release_date': data['releaseDate'],
            'purchase_url': {'soho': data['url']}
        }
        
        if data['details']:
            detail_entry = {
                'item_number': item_number,
                'name': data['name'],
                'release_code': release_code,
                'url': data['url']
            }
            
            if 'Product Configuration' in data['details']:
                config_text = data['details']['Product Configuration']
                parsed_config = parse_product_configuration(config_text)
                detail_entry['configuration'] = parsed_config
            
            for key, value in data['details'].items():
                if key != 'Product Configuration':
                    detail_entry[key.lower().replace(' ', '_')] = value
            
            product_details[item_number] = detail_entry
        
        releases[release_code][data['name']] = product_entry
    
    yaml_dir = output_dir / 'releases'
    yaml_dir.mkdir(exist_ok=True)
    
    for release_code, products_dict in sorted(releases.items()):
        yaml_data = {
            'code': release_code,
            'products': products_dict
        }
        
        yaml_file = yaml_dir / f'{release_code.upper()}.yaml'
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    if product_details:
        details_file = output_dir / 'product_details.json'
        with open(details_file, 'w', encoding='utf-8') as f:
            json.dump(product_details, f, indent=2, ensure_ascii=False)
        print(f"✓ Product details saved to {details_file}")
    
    if unknown_codes:
        print("Unknown item codes found:")
        for code in unknown_codes[:5]:
            print(f"  - {code}")


if __name__ == "__main__":
    main()