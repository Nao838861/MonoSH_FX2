"""ROMの全敵弾行データと共有コードを独立したword合成へ照合する。"""
import hashlib,json,struct
from pathlib import Path
from sa1_left_hints import physical

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/sa1_game'


def decode(code,first=0):
    masks=[];p=0;y=4
    while code[p]!=0x6b:
        op=code[p]
        if op==0xb7:
            assert code[p:p+3]==b'\xb7\xaa\x9d'
            assert struct.unpack_from('<H',code,p+3)[0]==(first+len(masks))*2
            mask=0;p+=5
        elif op==0xbd:
            assert struct.unpack_from('<H',code,p+1)[0]==(first+len(masks))*2
            assert code[p+3]==0x29
            mask=struct.unpack_from('<H',code,p+4)[0]
            assert code[p+6:p+9]==b'\x17\xaa\x9d'
            assert struct.unpack_from('<H',code,p+9)[0]==(first+len(masks))*2
            p+=11
        else:mask=65535
        assert code[p:p+2]==b'\xc8\xc8'
        p+=2;y+=2;masks.append(mask)
    assert p+1==len(code)
    return masks


def main():
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    config=json.loads((BUILD/'manifest.json').read_text());assert config['bulletShapes']
    seen=set();shapes={};rows=words=clip_cases=0
    for asset in (6,7,8,37):
        for w in range(1,256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            if not block:continue
            for entry in range(rom[0x7f0000+block]):
                desc=struct.unpack_from('<H',rom,0x7f0000+block+1+entry*10+1)[0]
                for variant in range(12):
                    ptr=int.from_bytes(rom[0x7f0000+desc+variant*3:0x7f0000+desc+variant*3+3],'little')
                    # 元素材の高さ。縦の倍率・反転は実行時の8.8位置で選ぶ。
                    ah={6:64,7:64,8:60,37:44}[asset]
                    p=physical(ptr)
                    for row in range(ah):
                        address=int.from_bytes(rom[p+row*3:p+row*3+3],'little')
                        if address in seen:continue
                        seen.add(address);r=physical(address)
                        shape=struct.unpack_from('<H',rom,r)[0]
                        count=rom[r+3]
                        if shape not in shapes:
                            start=0x430000+shape
                            code=rom[start+3:start+3+rom[start]]
                            masks=decode(code)
                            entries=rom[start+3+len(code):start+4+len(code)+len(masks)]
                            assert len(entries)==len(masks)+1
                            for first in range(len(masks)+1):
                                for last in range(first,len(masks)+1):
                                    assert decode(code[entries[first]:entries[last]]+b'\x6b',first)==masks[first:last]
                            values=[sum((0 if mask&(15<<(n*4)) else 1+(i*7+n*3)%15)<<(n*4) for n in range(4)) for i,mask in enumerate(masks)]
                            for origin in range(-len(masks)*2-2,131):
                                background=[(i*73+shape*37)&255 for i in range(128)]
                                expected=background.copy();actual=background.copy()
                                for i,value in enumerate(values):
                                    for byte in range(2):
                                        x=origin+i*2+byte
                                        if 0<=x<128:expected[x]=(expected[x]&((masks[i]>>(byte*8))&255))|((value>>(byte*8))&255)
                                if origin<128 and origin+len(masks)*2>0:
                                    first=max(0,(-origin+1)//2)
                                    last=min(len(masks),(128-origin)//2)
                                    for i in range(first,last):
                                        x=origin+i*2
                                        assert 0<=x<127
                                        actual[x]=(actual[x]&(masks[i]&255))|(values[i]&255)
                                        actual[x+1]=(actual[x+1]&(masks[i]>>8))|(values[i]>>8)
                                    if origin<0 and origin&1:actual[0]=(actual[0]&(masks[first-1]>>8))|(values[first-1]>>8)
                                    if origin&1 and last<len(masks):actual[127]=(actual[127]&(masks[last]&255))|(values[last]&255)
                                assert actual==expected,(shape,origin)
                                clip_cases+=1
                            opaque=sum(1<<i for i,m in enumerate(masks) if i<16 and m==0)
                            assert struct.unpack_from('<H',rom,start+1)[0]==opaque
                            shapes[shape]=masks
                        masks=shapes[shape];assert len(masks)==count
                        for i,mask in enumerate(masks):
                            value=struct.unpack_from('<H',rom,r+4+i*2)[0]
                            reference=sum((15 if (value>>(4*n))&15==0 else 0)<<(4*n) for n in range(4))
                            assert mask==reference,(hex(address),i,mask,reference)
                            background=(address*49157+i*31337)&65535
                            actual=(background&mask)|value
                            expected=sum((((value>>(4*n))&15) or ((background>>(4*n))&15))<<(4*n) for n in range(4))
                            assert actual==expected
                            words+=1
                        rows+=1
    report={'romSha256':hashlib.sha256(rom).hexdigest(),'rows':rows,'words':words,'shapes':len(shapes),'clipCases':clip_cases}
    (BUILD/'bullet_shapes_verified.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report)


if __name__=='__main__':main()
