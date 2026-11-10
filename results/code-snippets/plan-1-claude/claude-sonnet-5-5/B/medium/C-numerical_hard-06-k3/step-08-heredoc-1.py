s=open('a.py').read()
old=s[s.index("Sp=np.zeros"):s.index("S2=Sp.T@Sp")+len("S2=Sp.T@Sp")]
new='''S2=np.zeros((n,n))
for j,d in enumerate(dets):
    for i in range(5):
        for k in range(5):
            r=ann(d,2*k)
            if r is None: continue
            r2=cre(r[0],2*k+1)
            if r2 is None: continue
            s1=r[1]*r2[1]
            r3=ann(r2[0],2*i+1)
            if r3 is None: continue
            r4=cre(r3[0],2*i)
            if r4 is None: continue
            S2[idx[r4[0]],j]+=s1*r3[1]*r4[1]'''
open('a.py','w').write(s.replace(old,new))
