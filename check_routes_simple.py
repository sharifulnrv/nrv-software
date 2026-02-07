from app import app

def check():
    with app.app_context():
        # Print all cleaning rules
        for rule in app.url_map.iter_rules():
            if 'edit' in str(rule):
                print(f"Rule: {rule}, Methods: {rule.methods}")

if __name__ == "__main__":
    check()
