from fit import *
for B,C in [(0,0),(900,0),(0,4000)]:
    eq,ed=levels(B,C,1000.)
    print(B,C,"quartets",np.round(eq,1)); print("  doublets",np.round(ed,1))
