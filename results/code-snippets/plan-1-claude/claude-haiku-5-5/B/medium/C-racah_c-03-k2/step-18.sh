cat > go3.py << 'EOF'
exec(open('fit2.py').read())
best=None
for F2g in [40000,60000,80000]:
  for F4g in [30000,45000]:
    for Dqg in [1800,2000,2200]:
        r=least_squares(resid,[Dqg,F2g,F4g],bounds=([500,5000,5000],[4000,200000,200000]),xtol=1e-12,ftol=1e-12,gtol=1e-12)
        if best is None or r.cost<best.cost: best=r
p=best.x; print("fit Dq,F2,F4 =",p,"cost",best.cost,"resid",best.fun)
Dq,F2,F4=p
B=(9*F2-5*F4)/441; C=35*F4/441
print("Dq=%.1f B=%.1f C=%.1f C/B=%.3f"%(Dq,B,C,C/B))
print(energies(p))
EOF
python3 go3.py