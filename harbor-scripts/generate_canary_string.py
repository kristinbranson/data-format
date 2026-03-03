import random
import string

def generate_canary(length=12):
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{suffix}"

if __name__ == "__main__":
    print(generate_canary())