

var1 = 'Hello, World'
var2 = "Python Runoob"

print("var1[0]:", var1[0])
print("var2[1:5]:", var2[1:5])

import time

for i in range(101):
    bar = '[' + '=' * (i // 2) + ' ' * (50 - i // 2) + ']'
    print(f"\r{bar} {i:3}%", end='', flush=True)
    time.sleep(0.05)
print()
    