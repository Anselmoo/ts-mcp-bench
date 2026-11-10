import numpy as np, itertools, pickle
t=pickle.load(open('fine.pkl','rb'))
obs=np.array([29360,29620,31640.])
out=[]
for r in sorted(t):
    ex=[v for v,m in t[r][1:]]; mult=[m for v,m in t[r][1:]]
    for a,b,c in itertools.combinations(range(len(ex)),3):
        v=np.array([ex[a],ex[b],ex[c]])
        B=np.dot(v,obs)/np.dot(v,v)
        res=np.sqrt(np.mean((B*v-obs)**2))
        out.append((res,r,B,(a+1,b+1,c+1),(mult[a],mult[b],mult[c])))
out.sort(key=lambda x:x[0])
for o in out[:12]: print(round(o[0],1),o[1],round(o[2],1),o[3],o[4])
