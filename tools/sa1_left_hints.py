"""大きな草・木の左端クリップを、ROM内の途中命令へ直接接続する。"""
import json,struct
from sa1_prescaled import address


def physical(a):
    bank=a>>16;low=a&65535
    if bank>=0xc0:return (bank-0xc0)*65536+low+0x400000
    if bank>=0x80:return (bank-0x80)*32768+(low&32767)+0x200000
    return bank*32768+(low&32767)


def inline_records(rom,packing):
    """実ROMの全対象寸法からheaderをたどる。検証用JSONの列挙漏れに依存しない。"""
    pointers=set()
    for asset,minimum in packing['minimumWidths'].items():
        for width in range(int(minimum),256):
            block=struct.unpack_from('<H',rom,0x7f0000+int(asset)*512+width*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                entry=0x7f0000+block+1+i*10;desc=struct.unpack_from('<H',rom,entry+1)[0]
                for parity in range(6 if int(asset)==31 else 2):
                    chain=physical(int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little'))
                    for row in range(rom[entry]):
                        p=chain+row*11
                        assert rom[p]==0xa9 and rom[p+7]==0x22
                        pointers.add(int.from_bytes(rom[p+8:p+11],'little'))
    assert len(pointers)==packing['kernels']
    return [(ptr,int.from_bytes(rom[physical(ptr)-5:physical(ptr)-2],'little')) for ptr in sorted(pointers)]


def build(rom,dest,compressed=False,use_spare=False,extra_min_width=0,inline=False,flame=False):
    cursor=json.loads((dest/'compiled_game_packing.json').read_text())['payloadEnd']
    spare_ranges=((0x5f6fe0,0x5f8000),(0x5f9200,0x5fc000)) if use_spare else ()
    spare_cursors=[a for a,b in spare_ranges]
    for a,b in spare_ranges:assert not any(rom[a:b])
    def alloc(raw,cross_bank=False):
        nonlocal cursor
        raw=bytes(raw)
        if not cross_bank:
            for i,(a,b) in enumerate(spare_ranges):
                p=spare_cursors[i]
                if p+len(raw)<=b:
                    rom[p:p+len(raw)]=raw;spare_cursors[i]+=len(raw);return address(p)
        if not cross_bank and (cursor&65535)+len(raw)>65536:cursor=(cursor+65535)&~65535
        if cursor<0x7eb000 and cursor+len(raw)>0x7e0000:cursor=0x7eb000
        assert cursor+len(raw)<=0x7f0000,hex(cursor+len(raw))
        result=address(cursor);rom[cursor:cursor+len(raw)]=raw;cursor+=len(raw);return result
    pointers=set()
    targets={asset:64 for asset in (0,2,3,5)}
    if extra_min_width:targets[39]=extra_min_width
    if flame:targets[31]=64
    for asset,minimum in targets.items():
        for w in range(minimum,256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                entry=0x7f0000+block+1+i*10;h=rom[entry]
                desc=struct.unpack_from('<H',rom,entry+1)[0]
                for parity in range(6 if asset==31 else 2):
                    a=int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little')
                    offset=physical(a)
                    for y in range(h):
                        p=offset+y*11
                        assert rom[p]==0xa9 and rom[p+7]==0x22
                        pointers.add(int.from_bytes(rom[p+8:p+11],'little'))
    if inline:
        assert compressed
        records={ptr:int.from_bytes(rom[physical(ptr)-5:physical(ptr)-2],'little') for ptr in sorted(pointers)}
        unique={}
        for ptr,hint in records.items():
            p=physical(ptr);q=physical(hint);n=(rom[p-1]+1)//2+1
            size=1+3*((n+7)//8) if rom[q]==128 else n
            unique[hint]=size
        info={'assets':list(targets),'minimumWidths':targets,'minimumWidth':64,'kernels':len(records),'uniqueHintTables':len(unique),'hintBytes':sum(unique.values()),'hintBytesPerEntry':1,'hashSlots':0,'hashBytes':0,'payloadEnd':cursor,'compressed':True,'spareRanges':[],'inlineHeaders':True}
        (dest/'left_hints_records.json').write_text(json.dumps(list(records.items()))+'\n')
        (dest/'left_hints.inc').write_text('LEFT_HINT_TABLE=$000000\nLEFT_HINT_MASK=0\n',encoding='utf-8')
        (dest/'left_hints_packing.json').write_text(json.dumps(info,indent=2)+'\n')
        print(info)
        return rom
    slots=1
    while slots<(len(pointers)*6//5 if extra_min_width else len(pointers)*3//2):slots*=2
    records={};table=bytearray(slots*6);unique={};total=0
    # 大きなhashを先に置き、最終bankへの丸めで空きを浪費しない。
    target=alloc(table,cross_bank=True)
    probes=[]
    for ptr in sorted(pointers):
        p=physical(ptr);length=rom[p-2];extent=rom[p-1]
        code=rom[p:p+length];assert code[-1]==0x6b
        stores=[];begin=0;acc=0
        for i in range(0,length-1,3):
            op=code[i];v=struct.unpack_from('<H',code,i+1)[0]
            if op==0xa9:acc=v
            if op==0x9d:stores.append((v,begin,acc));begin=i+3
        encoded=bytearray()
        for word in range((extent+1)//2+1):
            item=next(((begin,acc) for off,begin,acc in stores if off+1>=word*2),(length-1,0))
            assert item[0]%3==0
            # 初期Aが必要なのは、直前の定数を再使用するSTAで開始するときだけ。
            if code[item[0]]==0x9d:
                previous=item[0]-3
                while code[previous]!=0xa9:
                    previous-=3
                    assert previous>=0
                assert struct.unpack_from('<H',code,previous+1)[0]==item[1]
            encoded+=bytes((item[0]//3,))
        key=bytes(encoded)
        if compressed:
            from analyze_sa1_hint_compression import compress
            key=compress(key)
        if key not in unique:unique[key]=alloc(key);total+=len(key)
        records[ptr]=unique[key]
        slot=((ptr&65535)>>1 ^ ((ptr>>16)<<3))&(slots-1)
        attempts=1
        while table[slot*6:slot*6+3]!=bytes(3):slot=(slot+1)&(slots-1);attempts+=1
        probes.append(attempts)
        table[slot*6:slot*6+6]=ptr.to_bytes(3,'little')+unique[key].to_bytes(3,'little')
    offset=physical(target)
    rom[offset:offset+len(table)]=table
    (dest/'left_hints.inc').write_text(f'LEFT_HINT_TABLE=${target:06x}\nLEFT_HINT_MASK={slots-1}\n',encoding='utf-8')
    info={'assets':list(targets),'minimumWidths':targets,'minimumWidth':64,'kernels':len(records),'uniqueHintTables':len(unique),'hintBytes':total,'hintBytesPerEntry':1,'hashSlots':slots,'hashBytes':len(table),'hashLoad':len(records)/slots,'payloadEnd':cursor,'compressed':compressed,'spareRanges':[dict(begin=a,end=b,used=c-a) for c,(a,b) in zip(spare_cursors,spare_ranges)]}
    info.update(hashMaxProbes=max(probes),hashMeanProbes=sum(probes)/len(probes))
    (dest/'left_hints_packing.json').write_text(json.dumps(info,indent=2)+'\n')
    print(info)
    return rom
