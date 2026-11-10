cd <SANDBOX_TMP>/w && sed -i 's/if sum(so\[i\]\[1\] for i in d)==3\]/]/' d4.py && cat >> d4.py << 'EOF'
EOF
python3 - << 'EOF'
src=open('<SANDBOX_TMP>/w/d4.py').read()
src=src.replace("Spm=onebody(Sp); S2=Spm.T@Spm+2*np.eye(N)","""Spm=onebody(Sp)
Sz=np.diag([sum(so[i][1]-0.5 for i in D) for D in dets])
S2=Spm.T@Spm+Sz@Sz+Sz""")
open('<SANDBOX_TMP>/w/d4.py','w').write(src)
EOF
time python3 d4.py && echo done