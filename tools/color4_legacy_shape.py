"""白黒原画の透過・黒い模様を固定し、白い画素へ録画由来の色を載せる。"""
import numpy as np
from PIL import Image

# 白い画素に使う色はRGB合計384以上。従来の白黒化でも白へ戻る。
PALETTE = [[0,0,0],[1,1,1],[31,31,31],[17,17,18],[7,7,8],
           [10,31,8],[21,31,12],[24,16,9],[28,21,14],[31,9,9],
           [31,29,3],[9,17,31],[12,25,31],[24,10,28],[31,16,2],[25,25,25]]
RECORDED_PLAYER = {9,15,16,17,18,28,29,30}
LEGACY_ASSETS = set(range(44)) - RECORDED_PLAYER - {10}

def colors_for(asset):
    if asset in (0,4):return [5,6,7,8],5
    if asset==1:return [5,6,7,8],7
    if asset==2:return [3,15,2],3
    if asset==3:return [3,15,2,9],3
    if asset in (5,31,39,40,41):return [9,10,14,2,8],14
    if asset in (6,37):return [13,2,15],13
    if asset==7:return [11,12,2,15],11
    if asset==8:return [9,14,2,15],9
    if asset in (11,12,32,33,34,35,36):return [3,15,2,13],3
    if asset in (13,14):return [5,6,7,8,10,2,15],5
    if 19<=asset<=27:return [8,9,11,12,2,15],11
    return [2],2

def preserve_shape(legacy,hint,asset):
    """色のヒントの欠損部分も、元原画の形と白黒を必ず復元する。"""
    base=np.array(legacy.convert('RGBA'))
    sample=np.array(hint.convert('RGBA').resize(legacy.size,Image.Resampling.NEAREST))
    palette=np.array(PALETTE,dtype=np.int32);rgb=palette*8+(palette>>2)
    choices,default=colors_for(asset)
    allowed=rgb[choices]
    assert np.all(allowed.sum(axis=1)>=384)
    assert np.all(np.array(Image.fromarray(allowed.astype(np.uint8)[None,:,:]).convert('L'))>=128)
    nearest=((sample[:,:,:3,None].astype(np.int32)-allowed.T[None,None,:,:])**2).sum(axis=2).argmin(axis=2)
    paint=allowed[nearest]
    paint[sample[:,:,3]<128]=rgb[default]
    white=base[:,:,:3].astype(np.int32).sum(axis=2)>=384
    result=base.copy();result[:,:,:3]=rgb[1]
    result[white,:3]=paint[white]
    result[base[:,:,3]==0,:3]=0
    assert np.array_equal(result[:,:,3],base[:,:,3])
    assert np.array_equal(result[:,:,:3].astype(np.int32).sum(axis=2)>=384,
                          white & (base[:,:,3]!=0))
    return Image.fromarray(result)
