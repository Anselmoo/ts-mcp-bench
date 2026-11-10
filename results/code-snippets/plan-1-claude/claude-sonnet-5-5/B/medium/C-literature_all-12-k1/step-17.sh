cat > /dev/shm/t.py <<'E'
exec(open('/dev/shm/hdr.py').read())
H=build(930,970,4300)
print(abs(H-H.T).max(), abs(H).max())
print(abs(np.einsum('ia,jb,kc,ld,abcd->ijkl',U.conj(),U.conj(),U,U,V2).imag).max())
G=R2
print(abs(G-G.transpose(2,3,0,1)).max(),abs(G-G.transpose(1,0,3,2)).max(),abs(G-G.transpose(2,1,0,3)).max())
E
python3 /dev/shm/t.py