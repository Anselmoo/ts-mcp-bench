cd /dev/shm/d5 && cat << 'EOF' > t.py
exec(open('d5.py').read())
Us=[]
for R in G:
    Fp=forb(P@R); sw=np.sqrt(W)[:,None]
    Ut,res,rk,sv=np.linalg.lstsq(F*sw,Fp*sw,rcond=None)
    Us.append(Ut)
    print(np.round(np.abs(Ut.T@Ut-np.eye(5)).max(),6), np.round(np.abs(F*sw).T@(F*sw)-np.eye(5),3).max().round(6) if False else '', np.abs((F*sw).T@(F*sw)-np.eye(5)).max())
    break
print(np.round(Ut,3))
EOF
python3 t.py