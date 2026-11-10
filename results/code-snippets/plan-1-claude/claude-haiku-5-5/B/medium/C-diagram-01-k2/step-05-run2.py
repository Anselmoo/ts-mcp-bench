import pickle
res=pickle.load(open('res.pkl','rb'))
for k in sorted(res):
    L=res[k]
    print(k, len(L))
    print('   ', [(t,round(e,3)) for t,e in L[:8]])
