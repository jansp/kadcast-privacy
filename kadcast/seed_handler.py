# https://stackoverflow.com/questions/36304187/is-there-a-good-way-to-share-the-seed-of-random-between-modules-in-python
# file that stores the shared seed value
seed_val_file = "seed_val.txt"

def save_seed(val, filename=seed_val_file):
    with open(filename, "wb") as f:
        f.write(str(val).encode())

def load_seed(filename=seed_val_file):
    with open(filename, "rb") as f:
        return int(f.read())