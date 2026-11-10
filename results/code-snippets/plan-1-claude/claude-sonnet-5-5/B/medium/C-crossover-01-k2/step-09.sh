cd <SANDBOX_TMP>
sed -i 's/cc_\[key\]=float((-1)\*\*m\*5\*gaunt(2,k,2,-m,m-mp,mp))/cc_[key]=float((-1)**m*5*gaunt(2,k,2,-m,m-mp,mp))*float((4*np.pi\/(2*k+1))**0.5)/' a.py
grep -n "cc_\[key\]=" a.py
python3 a.py