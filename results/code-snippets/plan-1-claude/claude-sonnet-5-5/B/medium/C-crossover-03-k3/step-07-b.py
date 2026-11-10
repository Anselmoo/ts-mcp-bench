exec(open('a.py').read().split('for D in')[0])
H0,S=build(sel0,0)
w,v=np.linalg.eigh(H0)
s=np.diag(v.T@S@v)
e5=np.linalg.eigvalsh(build(sel2,0)[0])[0]
import collections
cnt=collections.Counter((round(x-e5),round(ss*1)) for x,ss in zip(w,s))
for k in sorted(cnt):print(k,cnt[k])
