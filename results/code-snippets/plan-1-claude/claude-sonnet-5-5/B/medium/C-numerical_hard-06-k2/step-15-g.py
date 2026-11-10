from b import lev
for Dq,B in [(2000,500),(2500,400),(3000,400)]:
    L=lev(Dq,B,4*B); print(Dq,B,[(round(x-L[0][0]),d) for x,d in L][:8])
