from d6 import *
# sanity: free ion check of Racah: C-only / B-only
w=singlet_levels(0.,1000.,4500.)
print(len(w))
g=groups(w); g0=g[0][0]
for x,n in g: print(round(x-g0,1),n)
