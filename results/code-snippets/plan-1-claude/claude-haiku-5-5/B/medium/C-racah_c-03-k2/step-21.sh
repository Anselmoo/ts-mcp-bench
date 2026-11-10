python3 - << 'EOF'
src=open('fit2.py').read()
src=src.replace("t2=[e for e,n in g if n==3][0]","t2=[e-e0 for e,n in g if n==3][0]").replace("t1=[e for e,n in g if n==3][1:]","t1=[e-e0 for e,n in g if n==3][1:]")
open('fit2.py','w').write(src)
EOF
cat > go5.py << 'EOF'
exec(open('fit2.py').read())
p0=[1917.,57015.,37800.]
print("resid at start", resid(p0))
r=least_squares(resid,p0,xtol=1e-14,ftol=1e-14,gtol=1e-14,x_scale=[1000,10000,10000])
print("fit",r.x,r.fun)
Dq,F2,F4=r.x
B=(9*F2-5*F4)/441; C=35*F4/441
print("Dq=%.1f B=%.1f C=%.1f C/B=%.3f"%(Dq,B,C,C/B))
g,gd=spectrum(F2,F4,Dq); e0=g[0][0]
print("quartets rel",[(round(e-e0,1),n) for e,n in g])
print("doublets rel lowest",[(round(e-e0,1),n) for e,n in gd[:6]])
EOF
python3 go5.py