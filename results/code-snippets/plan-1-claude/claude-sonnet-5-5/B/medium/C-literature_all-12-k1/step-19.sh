cd /dev/shm; python3 - <<'E'
E
sed -n 1p /dev/null
cat > /dev/shm/t2.py <<'E'
exec(open('/dev/shm/t.py').read())
A=H-H.T
ij=np.argwhere(abs(A)>0.5)
print(len(ij))
for i,j in ij[:6]:
    print(dets[i],dets[j],H[i,j],H[j,i])
E
cat /dev/shm/t.py >/dev/null 2>&1 || echo nofile