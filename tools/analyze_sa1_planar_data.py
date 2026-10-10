"""全縮小・横8位相を直接planar描画するデータの容量を、元絵のまま測る。"""
import argparse,json,struct
import numpy as np
from build_sa1_probe import assets,BUILD
from sa1_patterns import dimensions


def groups(row,phase):
    p=np.pad(row,(phase,(-len(row)-phase)%8))
    bits=(1<<np.arange(7,-1,-1)).astype(np.uint16)
    blocks=p.reshape(-1,8)
    masks=((blocks==0)*bits).sum(axis=1)
    planes=[(((blocks>>b)&1)*bits).sum(axis=1) for b in range(4)]
    return [(i,bytes((int(mask),*(int(p[i]) for p in planes))))
            for i,mask in enumerate(masks) if mask!=255]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--native-planes',action='store_true');args=ap.parse_args()
    variants=assets(); patterns=dimensions()
    rowdata=set(); dictionary=set(); sparse=set(); row_count=0; heightmaps=0
    local_dictionary_bytes=0;local_sparse_bytes=0;local_dense_bytes=0;local_assets=[]
    for asset,sizes in sorted(patterns.items()):
        local_groups=set();local_rows=set()
        ah,aw=variants[asset,0][1].shape
        for width in sorted({w for w,h in sizes}):
            ys=set()
            for w,h in sizes:
                if w==width:
                    ys.update(((np.arange(h)*(ah*256//h))>>8).tolist())
                    heightmaps+=h
            xs=(np.arange(width)*(aw*256//width))>>8
            for hue in range(3 if (asset,1) in variants else 1):
                pixels=variants[asset,hue][1]
                for y in sorted(ys):
                    row=pixels[y,xs]
                    for phase in range(8):
                        blocks=groups(row,phase)
                        # offset + mask + four planes, with row length prefix.
                        encoded=bytes((len(blocks),))+b''.join(bytes((i,))+v for i,v in blocks)
                        rowdata.add(encoded);row_count+=1
                        sparse.add(tuple(blocks)); dictionary.update(v for _,v in blocks)
                        local_rows.add(tuple(blocks));local_groups.update(v for _,v in blocks)
        ids=2 if len(local_groups)<=65535 else 3
        local_dictionary_bytes+=5*len(local_groups)
        sparse_bytes=sum(2+len(row)*(1+ids) for row in local_rows)
        dense_bytes=sum(2+(row[-1][0]-row[0][0]+1)*ids if row else 2 for row in local_rows)
        local_sparse_bytes+=sparse_bytes;local_dense_bytes+=dense_bytes
        local_assets.append(dict(asset=asset,groups=len(local_groups),idBytes=ids,rows=len(local_rows),denseBytes=dense_bytes,sparseBytes=sparse_bytes))
        print(json.dumps(dict(asset=asset,rows=len(rowdata),rawBytes=sum(map(len,rowdata)),groups=len(dictionary))),flush=True)
    id_bytes=2 if len(dictionary)<=65536 else 3
    result=dict(uniqueRows=len(rowdata),rowEntries=row_count,
        directDataBytes=sum(map(len,rowdata)),dictionaryGroups=len(dictionary),
        dictionaryGroupBytes=len(dictionary)*5,
        dictionaryRowBytes=sum(1+len(row)*(1+id_bytes) for row in sparse),
        dictionaryIdBytes=id_bytes,rowDescriptorsUpperBytes=row_count*3,
        heightRowMapsBytes=heightmaps,geometryPatterns=sum(map(len,patterns.values())),
        includesExecutableRenderer=False,includesGame=False,includesOriginalPackedFallback=False)
    result['dictionaryTotalBytes']=result['dictionaryGroupBytes']+result['dictionaryRowBytes']+result['rowDescriptorsUpperBytes']+heightmaps
    result['directTotalBytes']=result['directDataBytes']+result['rowDescriptorsUpperBytes']+heightmaps
    result['perAssetDictionaryBytes']=local_dictionary_bytes
    result['perAssetSparseRowBytes']=local_sparse_bytes
    result['perAssetDenseRowBytes']=local_dense_bytes
    result['perAssetSparseTotalBytes']=local_dictionary_bytes+local_sparse_bytes+result['rowDescriptorsUpperBytes']+heightmaps
    result['perAssetDenseTotalBytes']=local_dictionary_bytes+local_dense_bytes+result['rowDescriptorsUpperBytes']+heightmaps
    result['perAsset']=local_assets
    if args.native_planes:
        pair_codes=set();bit_codes=set()
        for row in rowdata:
            blocks=[row[i:i+6] for i in range(1,len(row),6)]
            origin=blocks[0][0] if blocks else 0
            for width,codes in ((2,pair_codes),(1,bit_codes)):
                for first in range(0,4,width):
                    code=bytearray();previous=None
                    for block in blocks:
                        offset=struct.pack('<H',(block[0]-origin)*32)
                        mask=block[1]*(257 if width==2 else 1)
                        value=int.from_bytes(block[2+first:2+first+width],'little')
                        if mask:
                            code+=b'\xbd'+offset+b'\x29'+mask.to_bytes(width,'little')
                            if value:code+=b'\x09'+value.to_bytes(width,'little')
                            previous=None
                        elif previous!=value:
                            code+=b'\xa9'+value.to_bytes(width,'little');previous=value
                        code+=b'\x9d'+offset
                    codes.add(bytes(code+b'\x6b'))
        result['pairPlaneKernelBytes']=sum(map(len,pair_codes))
        result['pairPlaneKernelCount']=len(pair_codes)
        result['bitPlaneKernelBytes']=sum(map(len,bit_codes))
        result['bitPlaneKernelCount']=len(bit_codes)
        result['splitPlaneDescriptorsExcluded']=True
    (BUILD/'planar_data_feasibility.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
