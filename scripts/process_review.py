import yaml
from categorize import categorize_with_hints

def process_review_file(input_file: str, output_file: str = None):
    """Read review.yaml, categorize products, and write results"""
    
    if output_file is None:
        output_file = input_file.replace('.yaml', '_categorized.yaml')
    
    # Read the YAML file
    with open(input_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    stats = {
        'total': 0,
        'categorized': 0,
        'high_confidence': 0,
        'medium_confidence': 0,
        'low_confidence': 0,
        'still_unknown': 0
    }
    
    # Process each vendor
    for vendor, products in data.items():
        if not products:
            continue
            
        print(f"\n{vendor}:")
        print("=" * 60)
        
        for product_name, product_data in products.items():
            stats['total'] += 1
            
            # Skip if already categorized
            if product_data.get('category') != 'UNKNOWN':
                continue
            
            # Try to categorize
            item_number = product_data.get('identifiers', {}).get('wcmgId', '')
            category, subtype, confidence = categorize_with_hints(product_name, item_number)
            
            # Update the product data
            old_category = product_data['category']
            old_subtype = product_data['subtype']
            
            product_data['category'] = category
            product_data['subtype'] = subtype
            product_data['confidence'] = round(confidence, 2)
            
            # Track statistics
            if category != 'UNKNOWN':
                stats['categorized'] += 1
                if confidence >= 0.9:
                    stats['high_confidence'] += 1
                    conf_label = "HIGH"
                elif confidence >= 0.7:
                    stats['medium_confidence'] += 1
                    conf_label = "MED"
                else:
                    stats['low_confidence'] += 1
                    conf_label = "LOW"
                
                print(f"  [{conf_label}] {product_name[:60]}")
                print(f"        {old_category}/{old_subtype} -> {category}/{subtype} ({confidence:.2f})")
            else:
                stats['still_unknown'] += 1
                print("[???] {product_name[:60]}")
                print("UNKNOWN")
    
    # Write the updated YAML
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
if __name__ == "__main__":
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else "review.yaml"
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    process_review_file(input_file, output_file)