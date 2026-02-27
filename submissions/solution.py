# 🌀 Mission 2: The Loop-de-Loop Machine

def power_check(level):
    if level > 80:
        return "CRITICAL POWER!"
    else:
        return "Stable"

# The machine starts its cycle
for i in range(1, 11):
    power_level = i * 10
    status = power_check(power_level)
    print(f"Loop {i}: Power is {power_level}%. Status: {status}")

print("Yee-haw! The machine is fully powered!")
