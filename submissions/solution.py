# 🌀 Logic Swap Test
# The 'if' is wrapping the loop, not inside it!

def check_system():
    print("Checking power...")

is_powered = True
if is_powered: # IF IS OUTSIDE
    for i in range(1, 5):
        check_system()
        print(f"Cycle {i}")
        # Missing 'if' here!
# Line 10: Padding to meet line count
# Line 11: More padding
