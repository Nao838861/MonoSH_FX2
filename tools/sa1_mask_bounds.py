"""物体ごとの左右端更新を省き、完成したtile集合から帯の左右端を求める。"""


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def dirty(text):
    old='''  lda dirty_left
  cmp $0120,x
  bcs :+
  sta $0120,x
:
  lda dirty_right
  cmp $0122,x
  bcc :+
  sta $0122,x
:
'''
    text=change(text,old,'')
    text=change(text,'  lda #128\n  sta $0120,x\n  stz $0122,x\n','')
    text=change(text,'pipeline_merge:\n  jsl sa1_occupancy_capture',
        'pipeline_merge:\n  jsl sa1_mask_bounds\n  jsl sa1_occupancy_capture')
    return '.setcpu "65816"\n.import sa1_mask_bounds: far\n'+text


def row(text):
    return change(text,'''  lda drLeft
  cmp $0120,x
  bcs :+
  sta $0120,x
:
  lda drRight
  cmp $0122,x
  bcc :+
  sta $0122,x
:
''','')


def table(wide=False):
    values=[]
    for offset in (range(0,128,32) if wide else (0,)):
        for mask in range(256):
            lo=(((mask&-mask).bit_length()-1)*4 if mask else 32)+offset
            hi=mask.bit_length()*4+offset
            values.append(lo|hi<<8)
    assert len(values)==(1024 if wide else 256)
    return '.segment "GSU"\n.export sa1_byte_extents: far\nsa1_byte_extents:\n'+''.join('  .word '+','.join(str(v) for v in values[i:i+16])+'\n' for i in range(0,len(values),16))
