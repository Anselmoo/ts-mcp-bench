exec(open('fit.py').read().split('print("Dq=0')[0])
def groups(p):
    e=build(*p); vals=[];mult=[]
    for x in e:
        if vals and abs(x-vals[-1])<1e-6: mult[-1]+=1
        else: vals.append(x); mult.append(1)
    return np.array(vals),mult
print(groups((715,1000,4000)))
best=None
for Dq in np.arange(600,900,10):
  for B in np.arange(500,1300,20):
    for C in np.arange(2000,6000,100):
      vals,mult=groups((Dq,B,C))
      if len(vals)!=4: continue
      nu_=vals[1:]-vals[0]
      r=np.sum((nu_-obs)**2)
      if best is None or r<best[0]: best=(r,Dq,B,C,nu_,mult)
print(best)
