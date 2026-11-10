cat >> chk.py << 'EOF'
print("fixed numeric")
def ints2(ma,mc,k,q):  # int Y_a^* Y_c  Y_kq (for second electron, uses Y_kq)
    return np.sum(W*np.conj(Y(2,ma))*Y(2,mc)*Y(k,q))
def I2(ma,mb,mc,md,k):
    tot=0
    for q in range(-k,k+1):
        tot+= ints(ma,mc,k,q)*ints2(mb,md,k,q)
    return 4*np.pi/(2*k+1)*tot
for (ma,mb,mc,md) in [(2,0,2,0),(1,0,0,1),(2,-1,1,0),(1,-1,1,-1),(2,0,0,2)]:
    a,b,c,d=[2*(m+2) for m in (ma,mb,mc,md)]
    for k in (2,4):
        F={0:0,2:0,4:0}; F[k]=1
        print((ma,mb,mc,md),k, round(Vint(a,b,c,d,F),6), round(I2(ma,mb,mc,md,k).real,6))
EOF
python3 chk.py | sed -n '/fixed/,$p'