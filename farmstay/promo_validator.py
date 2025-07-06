import csv
import sys
import json
import os

def validate_promo(promo_code):
    promo_file = os.path.join(os.path.dirname(__file__), "promocodes.csv")

    try:
        with open(promo_file, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["code"].strip().upper() == promo_code.strip().upper():
                    return {"valid": True, "discount": int(row["discount"])}
    except Exception as e:
        return {"valid": False, "discount": 0, "error": str(e)}

    return {"valid": False, "discount": 0}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"valid": False, "discount": 0, "error": "No promo code provided"}))
        sys.exit(1)

    promo_code = sys.argv[1]
    result = validate_promo(promo_code)
    print(json.dumps(result))
