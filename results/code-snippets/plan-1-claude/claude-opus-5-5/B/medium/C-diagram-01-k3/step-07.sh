cd $TMPDIR && cat > an2.py <<'EOF'
import pickle,numpy as np,json
B=828.
res=pickle.load(open('res.pkl','rb'))
par={'4A2':['F'],'4T2':['F'],'4T1':['F','P'],'2A1':['G'],'2E':['G','H','D','D'],'2T1':['G','H/P','H/P','P/H'],'2T2':['G','H','D','F','D'],'2A2':['F']}
pri={'4A2':0,'4T2':1,'4T1':2,'2E':3,'2T1':4,'2T2':5,'2A1':6,'2A2':7}
def lab(dq):
    r=res[dq]; cnt={}; out=[]
    for e,m,ir in r:
        k=f'{m}{ir}'; i=cnt.get(k,0); cnt[k]=i+1
        p=par.get(k,['?']*9)[i] if i<len(par.get(k,[])) else '?'
        out.append((e,k,p))
    e0=min(x[0] for x in out)
    out=[(round((e-e0)/B,6),k,p) for e,k,p in out]
    out.sort(key=lambda x:(round(x[0],4),pri[x[1]]))
    return out
pts=[]
for dq in [0,0.5,1,1.5,2,2.5,3,3.5,4]:
    o=lab(float(dq))
    lv=[{'term':f'{k[0]}{k[1:]}g({p})' if p!='?' else k,'e_over_b':round(e,3)} for e,k,p in o[:6]]
    pts.append({'dq_over_b':dq,'levels':lv})
    print(dq,[(l['term'],l['e_over_b']) for l in lv])
json.dump(pts,open('pts.json','w'))
EOF
python3 an2.py