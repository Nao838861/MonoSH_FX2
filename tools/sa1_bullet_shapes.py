"""敵弾の透明形状だけを共有コード化し、色データと分けて保持する。"""
import json,struct


class Shapes:
    def __init__(self):
        self.data=bytearray(b'\0')
        self.pointers={}

    def add(self,masks):
        key=tuple(masks)
        if key in self.pointers:return self.pointers[key]
        code=bytearray()
        entries=bytearray()
        opaque=0
        for i,mask in enumerate(masks):
            entries.append(len(code))
            offset=struct.pack('<H',i*2)
            if mask==0:
                if i<16:opaque|=1<<i
                code+=b'\xb7\xaa\x9d'+offset
            elif mask!=65535:
                code+=b'\xbd'+offset+b'\x29'+struct.pack('<H',mask)+b'\x17\xaa\x9d'+offset
            code+=b'\xc8\xc8'
        entries.append(len(code))
        code+=b'\x6b'
        assert len(code)<=255
        pointer=len(self.data)
        self.data+=bytes((len(code),))+struct.pack('<H',opaque)+code+entries
        assert len(self.data)<=65536
        self.pointers[key]=pointer
        return pointer

    def save(self,dest):
        (dest/'bullet_shapes.bin').write_bytes(self.data+bytes(65536-len(self.data)))
        (dest/'bullet_shapes_packing.json').write_text(json.dumps({
            'shapes':len(self.pointers),'bytes':len(self.data),'romBank':0xc3,
            'iramStart':0x500,'maxKernelBytes':255,
        },indent=2)+'\n')


def cpu(text):
    old='  lda #$c3\n  sta $4304\n  lda #1\n  sta $420b\n'
    assert text.count(old)==1
    text=text.replace(old,'  jsl compact_ppu_boot\n',1)
    old='  lda #2\n  sta $420c'
    assert text.count(old)==1
    text=text.replace(old,'shape_boot_blank:\n  lda $4212\n  bpl shape_boot_blank\n  lda #2\n  sta $420c',1)
    return '.setcpu "65816"\n.import compact_ppu_boot: far\n'+text


def finish(rom,build,labels,ppu):
    from sa1_compact_memory import packbits,unpackbits
    assert labels['__RODATA_SIZE__']+labels['__DATA_SIZE__']<=0x8000
    packed=packbits(ppu)
    assert len(packed)<=0x8000 and unpackbits(packed)==ppu
    rom[0x428000:0x428000+len(packed)]=packed
    rom[0x430000:0x440000]=(build/'bullet_shapes.bin').read_bytes()
    p=build/'bullet_shapes_packing.json'
    d=json.loads(p.read_text());d['ppuPackedBytes']=len(packed)
    p.write_text(json.dumps(d,indent=2)+'\n')


def pipeline(text):
    assert text.count('  lda #283\n')==1
    return text.replace('  lda #283\n','  lda #281\n',1)
