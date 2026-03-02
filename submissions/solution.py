def check_power(level):
    if level > 5:
        print("ATTACK! Power level is high!")
    else:
        print("DEFEND! Power level is low.")

for i in range(10):
    check_power(i)
    print(f"Checking level {i}")
    if i > 5:
        print("Warning: level exceeded!")
    else:
        print("Level is safe.")

print("All levels checked!")
print("Mission complete!")
