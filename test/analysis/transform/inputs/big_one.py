def source(filename):
    def decorator(fn):
        def wrapper():
            with open(filename, "r") as f:
                return fn(f.read())
        return wrapper
    return decorator


@source("users.csv")
def process_users(users):
    return users.upper()


process_users()