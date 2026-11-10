cd /tmp && python3 -c "
import scipy.special as s; print([n for n in dir(s) if 'sph' in n])"