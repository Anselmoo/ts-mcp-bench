obs=np.array([16700,26330,35020])
best=[]
for Dq in range(1200,3000,25):
  for B in range(200,900,10):
    L=lev(Dq,B,4*B); e=[x-L[0][0] for x,d in L]
    d=[d for x,d in L]
    cand=[(abs(e[1]-obs[0])+abs(e[2]-obs[1])+min(abs(e[i]-obs[2]) for i in (3,4,5)),Dq,B,[ (round(e[i]),d[i]) for i in range(1,7)])]
    best+=cand
best.sort(key=lambda t:t[0])
for b in best[:5]: print(b)
