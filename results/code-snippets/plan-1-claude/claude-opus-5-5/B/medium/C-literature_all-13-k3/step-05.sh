
cd <SANDBOX_TMP>; cat >> fit.py << 'EOF'
print('---')
for x0 in [[800,800,3200],[800,900,4000],[800,700,3000],[850,850,3800],[800,1000,3000]]:
    r=least_squares(res,x0,bounds=([500,300,1000],[1200,1200,6000]))
    print(x0,r.x,res(r.x),r.cost)
EOF
python3 fit.py | sed -n '/---/,$p'
