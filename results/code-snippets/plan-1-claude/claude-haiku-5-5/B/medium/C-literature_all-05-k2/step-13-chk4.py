from fit3 import *
for p in [(0,600,0),(0,0,3000),(0,600,3000),(2155,600,3000)]:
    g,dd=spec(p); E0=g[0]
    print(p,"Q",[(round(e-E0,1),m) for e,m in clus(g)])
    print("   D",[(round(e-E0,1),m) for e,m in clus(dd)])
