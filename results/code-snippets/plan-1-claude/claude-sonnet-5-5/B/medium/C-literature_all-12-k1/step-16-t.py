exec(open('/dev/shm/hdr.py').read())
print([(round(x),n) for x,n in lev(930,970,4300) if x<26000])
