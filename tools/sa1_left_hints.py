"""大きな草・木の左端クリップを、ROM内の途中命令へ直接接続する。"""
import json,struct
from sa1_prescaled import address


def physical(a):
    bank=a>>16;low=a&65535
    if bank>=0xc0:return (bank-0xc0)*65536+low+0x400000
    if bank>=0x80:return (bank-0x80)*32768+(low&32767)+0x200000
    return bank*32768+(low&32767)


def build(rom,dest):
    cursor=json.loads((dest/'compiled_game_packing.json').read_text())['payloadEnd']
    def alloc(raw,cross_bank=False):
        nonlocal cursor
        raw=bytes(raw)
        if not cross_bank and (cursor&65535)+len(raw)>65536:cursor=(cursor+65535)&~65535
        if cursor<0x7eb000 and cursor+len(raw)>0x7e0000:cursor=0x7eb000
        assert cursor+len(raw)<=0x7f0000,hex(cursor+len(raw))
        result=address(cursor);rom[cursor:cursor+len(raw)]=raw;cursor+=len(raw);return result
    pointers=set()
    for asset in (0,2,3,5):
        for w in range(64,256):
            block=struct.unpack_from('<H',rom,0x7f0000+asset*512+w*2)[0]
            if not block:continue
            for i in range(rom[0x7f0000+block]):
                entry=0x7f0000+block+1+i*10;h=rom[entry]
                desc=struct.unpack_from('<H',rom,entry+1)[0]
                for parity in (0,1):
                    a=int.from_bytes(rom[0x7f0000+desc+parity*3:0x7f0000+desc+parity*3+3],'little')
                    offset=physical(a)
                    for y in range(h):
                        p=offset+y*11
                        assert rom[p]==0xa9 and rom[p+7]==0x22
                        pointers.add(int.from_bytes(rom[p+8:p+11],'little'))
    slots=1
    while slots<len(pointers)*3//2:slots*=2
    records={};table=bytearray(slots*6);unique={};total=0
    # 大きなhashを先に置き、最終bankへの丸めで空きを浪費しない。
    target=alloc(table,cross_bank=True)
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
        if key not in unique:unique[key]=alloc(encoded);total+=len(encoded)
        records[ptr]=unique[key]
        slot=((ptr&65535)>>1 ^ ((ptr>>16)<<3))&(slots-1)
        while table[slot*6:slot*6+3]!=bytes(3):slot=(slot+1)&(slots-1)
        table[slot*6:slot*6+6]=ptr.to_bytes(3,'little')+unique[key].to_bytes(3,'little')
    offset=physical(target)
    rom[offset:offset+len(table)]=table
    (dest/'left_hints.inc').write_text(f'LEFT_HINT_TABLE=${target:06x}\nLEFT_HINT_MASK={slots-1}\n',encoding='utf-8')
    info={'assets':[0,2,3,5],'minimumWidth':64,'kernels':len(records),'uniqueHintTables':len(unique),'hintBytes':total,'hintBytesPerEntry':1,'hashSlots':slots,'hashBytes':len(table),'payloadEnd':cursor}
    (dest/'left_hints_packing.json').write_text(json.dumps(info,indent=2)+'\n')
    print(info)
    return rom
