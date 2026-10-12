"""全寸法のnative/弾データと逆順行の全右端境界を旧ROMへ照合する。"""
import argparse,hashlib,json,struct
from pathlib import Path
from build_sa1_game import BUILD
from build_sa1_probe import assets
from sa1_left_hints import physical
from verify_sa1_stack_rows import execute_native
from sa1_reverse_explosions import SELECTOR,BANK_TABLE,decode_hint


def u16(data,pos):return struct.unpack_from('<H',data,pos)[0]
def ptr(data,pos):return int.from_bytes(data[pos:pos+3],'little')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--reference-rom',type=Path,default=BUILD/'fifobwmap_v2_build/MonoSHSA1_4bpp_game.sfc')
    args=ap.parse_args()
    original=args.reference_rom.read_bytes();rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    config=json.loads((BUILD/'manifest.json').read_text());minimum=config['reverseExplosionsMinWidth']
    assert config['reverseExplosions'] and hashlib.sha256(rom).hexdigest()==config['romSha256']
    variants=assets();patterns=0;native_rows=0;bullet_rows=0;changed=set()
    initial=bytes((x*73+39)&255 for x in range(256))
    for asset in range(44):
        phases=3 if (asset,1) in variants else 1
        for width in range(256):
            a=u16(original,0x7f0000+asset*512+width*2);b=u16(rom,0x7f0000+asset*512+width*2)
            assert bool(a)==bool(b),f'geometry omitted: {asset}/{width}'
            if not a:continue
            a+=0x7f0000;b+=0x7f0000
            assert original[a]==rom[b]
            for i in range(rom[b]):
                x=a+1+i*10;y=b+1+i*10;h=rom[y];patterns+=1
                assert original[x]==h and original[x+3:x+7]==rom[y+3:y+7]
                da=u16(original,x+1)+0x7f0000;db=u16(rom,y+1)+0x7f0000
                bullet=asset in (6,7,8,37)
                for n in range(phases*(4 if bullet else 2)):
                    ca=physical(ptr(original,da+n*3));cb=physical(ptr(rom,db+n*3))
                    if bullet:
                        ah=variants[asset,n//4][1].shape[0]
                        for row in range(ah):
                            pa=physical(ptr(original,ca+row*3));pb=physical(ptr(rom,cb+row*3))
                            size=4+original[pa+3]*2
                            assert original[pa:pa+size]==rom[pb:pb+size]
                            bullet_rows+=1
                        continue
                    for row in range(h):
                        qa=ca+row*11;qb=cb+row*11
                        assert original[qa:qa+8]==rom[qb:qb+8],f'row origin changed: {asset}/{width}/{h}'
                        pa=physical(ptr(original,qa+8));pb=physical(ptr(rom,qb+8))
                        old_code=original[pa:pa+original[pa-2]];new_code=rom[pb:pb+rom[pb-2]]
                        assert original[pa-1]==rom[pb-1]
                        if asset in (40,41) and width>=minimum:
                            if (pa,pb) not in changed:
                                assert execute_native(old_code,initial)==execute_native(new_code,initial)
                                changed.add((pa,pb))
                        else:assert old_code==new_code
                        native_rows+=1
    assert patterns==1492
    candidates=[]
    if config.get('reverseInlineHints'):
        candidates=[(p,physical(ptr(rom,p-5)),rom[p-1]) for a,p in changed]
    else:
        base=SELECTOR;count=u16(rom,base)
        for i in range(count):
            for parity in range(2):
                entry=u16(rom,base+2+i*8);height=rom[0x7f0000+entry]
                rows=physical(ptr(rom,base+4+i*8+parity*3))
                desc=u16(rom,0x7f0000+entry+1)
                native=physical(ptr(rom,0x7f0000+desc+parity*3))
                for row in range(height):
                    if config.get('reverseRecordsCompact'):
                        q=rows+row*6;control=u16(rom,q+4)
                        code_ptr=u16(rom,q)|(rom[BANK_TABLE+(control>>11&15)]<<16)
                        hint_ptr=u16(rom,q+2)|((0xfe if control&0x8000 else 0xdf)<<16)
                        origin=(control&31)*2;extent=(control>>5&63)*2
                    else:
                        q=rows+row*8;code_ptr=ptr(rom,q);hint_ptr=ptr(rom,q+3);origin=rom[q+6];extent=rom[q+7]
                    assert code_ptr==ptr(rom,native+row*11+8)
                    assert origin==u16(rom,native+row*11+1)-row*128
                    assert extent==rom[physical(code_ptr)-1]
                    candidates.append((physical(code_ptr),physical(hint_ptr),extent))
    checked=set();boundaries=0
    for p,hint,extent in candidates:
        code=rom[p:p+rom[p-2]];key=(p,hint)
        if key in checked:continue
        expected=execute_native(code,initial)
        for limit in range(extent+1):
            start=decode_hint(rom,hint,(limit+1)//2) if config.get('reverseHintsCompressed') else rom[hint+(limit+1)//2]
            actual=execute_native(code[start:],initial)
            actual[limit]=initial[limit]
            assert actual[:limit]==expected[:limit] and actual[limit:]==initial[limit:]
            boundaries+=1
        checked.add(key)
    result=dict(geometryPatterns=patterns,nativeRowUses=native_rows,bulletRowUses=bullet_rows,
        reversedKernelPairs=len(changed),rightHintKernels=len(checked),rightByteBoundaries=boundaries,
        referenceRomSha256=hashlib.sha256(original).hexdigest(),romSha256=config['romSha256'],gameIntegrated=True)
    (BUILD/'reverse_explosions_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result)


if __name__=='__main__':main()
