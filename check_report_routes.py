from app import app

def check():
    print("Checking Report Routes:")
    with app.app_context():
        for rule in app.url_map.iter_rules():
            if 'report' in str(rule):
                print(f"{rule} -> {rule.endpoint}")

if __name__ == "__main__":
    check()
