import numpy as np, itertools, pickle
table=pickle.load(open('table.pkl','rb'))
obs=np.array([29360,29620,31640.])
rs=sorted(table)
# levels excluding ground (index 0), take excitation energies e (per B=1)
res=[]
for r in rs:
    ex=[float(v) for v,m in table[r][1:]]  # excited levels, unique
    mult=[m for v,m in table[r][1:]]
    # try triples of excited levels (ordered) among first 8
    for a,b,c in itertools.combinations(range(8),3):
        ea,eb,ec=ex[a],ex[b],ex[c]
        # B from least squares: obs = B*e
        v=np.array([ea,eb,ec])
        B=np.dot(v,obs)/np.dot(v,v)
        resid=np.sqrt(np.mean((B*v-obs)**2))
        res.append((resid,r,B,(a+1,b+1,c+1),mult[a],mult[b],mult[c]))
res.sort(key=lambda x:x[0])
for x in res[:15]: print(round(x[0],1), x[1], round(x[2],1), x[3], x[4:])
