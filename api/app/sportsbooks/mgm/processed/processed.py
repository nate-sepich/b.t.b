import json

def load_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def get_list_info(data):
    if isinstance(data, list):
        info = {
            'length': len(data),
            'contents': data,
            'first_item': data[0] if data else None,
            'last_item': data[-1] if data else None
        }
        return info
    else:
        raise ValueError("The loaded data is not a list")

if __name__ == "__main__":
    file_path = 'api/app/sportsbooks/mgm/processed/mgm_latest.json'
    data = load_json(file_path)
    info = get_list_info(data)
    print(f"Length of list: {info['length']}")
    print(f"Contents of list: {info['contents']}")
    print(f"First item: {info['first_item']}")
    print(f"Last item: {info['last_item']}")