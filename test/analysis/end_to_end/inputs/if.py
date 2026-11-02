def process(condition):
    if condition:
        with open("users.csv", "r") as f:
            f.read()
    else:
        with open("config.json", "r") as f:
            f.read()

process(True)
process(False)
process(input())