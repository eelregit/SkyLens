from wigner_functions import *
import zarr
import time
lmax=3000 #1e4
wlmax=5e2 #no reason to choose a small number here as most j3 will be computed.
m1=-2
m2=2
m3=0

lmax=np.int(lmax)
wlmax=np.int(wlmax)

fname='temp/dask_wig3j_l{lmax}_w{wlmax}_{i}_reorder.zarr'

fname=fname.format(i=m2,lmax=lmax,wlmax=wlmax)
print('will save to ',fname)

lmax+=1
wlmax+=1
ncpu=8
l_step=100 #not used with dask
w_l=np.arange(wlmax)
l=np.arange(lmax)

lb=np.arange(lmax,step=l_step)
z1 = zarr.open(fname, mode='w', shape=(wlmax,lmax,lmax), #0-lmax
               chunks=(wlmax/10, lmax/10,lmax/10),
               dtype='float32',overwrite=True)

j_max=np.amax(lmax+lmax+wlmax+10)
calc_factlist(j_max)

from multiprocessing import Pool
def wig3j_recur_1d(j2s,m1,m2,m3,j3_outmax,j1):
    out_ij={}
    x=j2s>=j1
    for j2 in j2s[x]:
        out_ij[j2]=wig3j_recur(j1,j2,m1,m2,m3,j3_outmax=j3_outmax)
    return out_ij

def wig3j_recur_2d(j1b,j2b,m1,m2,m3,j3_outmax,step,z1_out):
    out= np.zeros((j3_outmax,min(step,lmax-j1b),min(step,lmax-j2b)))

    j1s=np.arange(j1b,min(lmax,j1b+step))
    j2s=np.arange(j2b,min(lmax,j2b+step))

    t1=time.time()
    funct=partial(wig3j_recur_1d, j2s,m1,m2,m3,j3_outmax)
    pool=Pool(10)
    out_ij=pool.map(funct,j1s,chunksize=1)
    pool.close()
    t2=time.time()
    print('pool done ',j1b,j2b,t2-t1)

    for j1 in np.arange(len(j1s)):
        for j2 in np.arange(len(j2s)):
            if j2s[j2]>=j1s[j1]:
                out[:,j1,j2]=out_ij[j1][j2s[j2]]
                
    z1[:,j1b:j1b+step,j2b:j2b+step]+=out
    
    for j1 in np.arange(len(j1s)):
        for j2 in np.arange(len(j2s)):
            if j2s[j2]==j1s[j1]:
                out[:,j1,j2]*=0 #don't want to add diagonal twice below.
    z1[:,j2b:j2b+step,j1b:j1b+step]+=out.transpose(0,2,1) #exploit j1-j2 symmetry
    t3=time.time()
    print('done ',j1b,j2b,t3-t1)
    return 0

t0=time.time()
for lb1 in lb:
    ww_out={}
    for lb2 in lb:
        if lb2<lb1: #we exploit j1-j2 symmetry and hence only compute for j2>=j1
            continue
        if np.absolute(lb2-lb1-l_step-1)>wlmax: #given j1-j2, there is a min j3 for non-zero values. If it falls outside the required j3 range, nothing to compute.
            continue
        print('doing ',lb1,lb2, 'step= ',l_step)
        t1=time.time()
        ww_out[lb2]=wig3j_recur_2d(lb1,lb2,m1,m2,m3,wlmax,l_step,z1)
    t2=time.time()
    print('done',lb1,t2-t1)
print('done all',t2-t0)
