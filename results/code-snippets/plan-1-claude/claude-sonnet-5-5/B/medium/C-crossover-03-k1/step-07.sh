cd <SANDBOX_TMP> && python3 -c "
exec(open('a.py').read().split('dets=')[0])
print(c(2,0,0),c(2,1,1),c(2,2,2),c(4,0,0),c(2,1,0),c(2,0,1),c(0,1,1))"