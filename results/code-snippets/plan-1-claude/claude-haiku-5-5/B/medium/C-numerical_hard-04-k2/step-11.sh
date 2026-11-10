cd . && python3 -c "
import pickle
t=pickle.load(open('table.pkl','rb'))
for r in [1.5,2.0,2.5,3.0,3.5]:
    print(r,[(round(float(v),3),m) for v,m in t[r][:9]])
"