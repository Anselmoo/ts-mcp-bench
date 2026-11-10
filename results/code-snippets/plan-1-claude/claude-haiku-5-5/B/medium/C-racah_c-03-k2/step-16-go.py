exec(open('fit2.py').read())
# explore
for p in [(1917,10000,5000),(1917,0,0)]:
    print(energies(p))
