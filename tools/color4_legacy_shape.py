"""元原画の輪郭を固定し、録画で確認した部位・階調に沿って着色する。"""
import numpy as np
from PIL import Image

# 自機はこの15色へ減色せず、録画由来の専用OBJパレットで描く。
PALETTE=[[0,0,0],[1,1,1],[31,31,31],[2,10,0],[10,31,8],
         [8,4,1],[28,22,18],[12,12,14],[18,18,21],
         [12,3,15],[31,23,31],[4,5,16],[20,25,31],
         [12,2,2],[31,22,19],[31,18,1]]
RECORDED_PLAYER={9,15,16,17,18,28,29,30}
LEGACY_ASSETS=set(range(44))-RECORDED_PLAYER-{10}
NORMAL_BULLETS={6,7,8,37}
TWO_TONE_ASSETS=LEGACY_ASSETS-NORMAL_BULLETS-{31}

def preserve_shape(legacy,hint,asset):
    """別姿勢の色を貼らず、元原画上の部位を塗り分ける。"""
    a=np.array(legacy.convert('RGBA'));opaque=a[:,:,3]>=128
    white=a[:,:,:3].astype(np.int32).sum(2)>=384
    y,x=np.indices(opaque.shape);h,w=opaque.shape
    pix=np.where(white,2,1)
    def region(mask,light,dark):
        pix[mask]=np.where(white[mask],light,dark)
    if asset in (0,1,4,13,14):
        region(opaque,4,3)
        if asset==4:region((y>=h*.77)&opaque,6,5)
        if asset==13:
            belly=(y>=h*(.64+.16*((x-w*.5)/(w*.5))**2))&opaque
            region(belly,6,5)
        if asset==14:
            horns=(y<h*.18)&((x<w*.27)|(x>w*.73))&opaque
            region(horns,6,5)
    elif asset in (2,3,11,12,32,33,34,35,36):
        region(opaque,8,7)
        if asset==3:
            cockpit=(x>w*.37)&(x<w*.63)&(y<h*.43)&opaque
            region(cockpit,14,13)
    elif asset in NORMAL_BULLETS:
        # 輪郭の主軸の短軸に沿って、左右対称の白い中央帯を作る。
        coords=np.column_stack((x[opaque],y[opaque])).astype(float)
        center=coords.mean(0);_,vectors=np.linalg.eigh(np.cov(coords.T))
        minor=vectors[:,0]
        distance=np.abs((x-center[0])*minor[0]+(y-center[1])*minor[1])
        radius=max(1,float(distance[opaque].max()))
        # 白は中央帯に限定。外側の同じ色相の2階調を固定ditherで補間する。
        level=(1-np.minimum(1,distance/radius))**.55
        bayer=np.array([[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]])
        shade=level>(bayer[y%4,x%4]+.5)/16
        pix=np.where(distance<radius*.18,2,np.where(shade,10,9))
    elif asset==31:
        r=np.sqrt(((x-(w-1)*.5)/(w*.5))**2+((y-(h-1)*.5)/(h*.5))**2)
        pix=np.where(r<.30,2,np.where(r<.70,10,9))
    elif asset in (5,39,40,41):
        r=np.sqrt(((x-w*.5)/(w*.5))**2+((y-h*.5)/(h*.5))**2)
        light=np.where(r<.36,2,np.where(r<.72,15,14))
        pix=np.where(white,light,13)
    elif 19<=asset<=27:
        light=np.where(y<h*.23,6,np.where(y<h*.51,14,12))
        pix=np.where(white,light,1)
    pix=np.where(opaque,pix,0)
    rgb=np.array(PALETTE,dtype=np.uint8);rgb=rgb*8+(rgb>>2)
    out=np.dstack((rgb[pix],a[:,:,3]))
    assert np.array_equal(out[:,:,3],a[:,:,3])
    if asset in TWO_TONE_ASSETS:
        recovered=(out[:,:,:3].astype(int).sum(2)>=384)&opaque
        assert np.array_equal(recovered,white&opaque),asset
    return Image.fromarray(out)
