from b import *
obs=np.array([22640,22930,25080])
def uniq(Dq,B):
    e=levels(Dq,B,4.6*B);e=e[e<1e5];e=e-e[:3].mean()
    e=e[3:]
    u=[]
    for x in e:
        if not u or x-u[-1]>15: u.append(x)
    return np.array(u)
best=[]
for D in range(1800,3300,50):
  for B in range(250,900,25):
    u=uniq(D,B)[:3]
    best.append((np.sum((u-obs)**2),D,B,u.round()))
best.sort(key=lambda t:t[0])
for b in best[:6]:print(b)
