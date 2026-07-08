try:
    x = 1
except ValueError as e:
    x = 2
except TypeError:
    x = 3
except:
    x = 4
else:
    x = 5
finally:
    x = 6