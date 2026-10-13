"""固定二面の交互所有順からSA-1でVRAM絶対宛先を用意する。"""
from sa1_fixed_map import change


def direct(text):
    text=change(text,'  ldx #0\nfixed_descriptor:', '''  ; generation 1は3000、以後は欠番なしで交互に所有する。
  lda $0198
  and #1
  beq prebank_page_zero
  lda #.loword(496-$3000)
  bra prebank_page_ready
prebank_page_zero:
  lda #496
prebank_page_ready:
  sta $c0
  ldx #0
fixed_descriptor:''')
    return change(text,'  sbc #496\n','  sbc $c0\n')


def pipeline(text):
    text=change(text,'  lda #512\n  sta pipe_records+212,x\n',
        '  lda pipe_records+6,x\n  clc\n  adc #512\n  sta pipe_records+212,x\n')
    text=change(text,'''  lda pipe_records+212,x
  ldx pipe_record_offset
  clc
  adc pipe_records+6,x
''','  lda pipe_records+212,x\n')
    text=change(text,'''  ; 全destinationは$8000未満。各ADC後もcarry=0を維持する。
  adc pipe_fast_page
''','')
    text=change(text,'=12*26', '=12*23')
    text=change(text,'.min(I,12)*26','.min(I,12)*23')
    # 非展開の条件付き経路も同じ絶対宛先を使う。
    text=change(text,'  clc\n  adc pipe_fast_page\n  sta f:$002116\n','  sta f:$002116\n')
    return text


def short_io(text):
    """DMA区間だけDB=00として、I/O書込みを短いabsolute命令にする。"""
    begin=text.index('pipe_fast_unroll_start:\n')
    end=text.index('pipe_fast_unroll_end:\n',begin)
    block=text[begin:end]
    assert block.count('  lda pipe_records-')==3
    block=block.replace('  lda pipe_records-','  lda f:$7e0000+pipe_records-')
    for address in ('4305','4302','2116'):
        block=change(block,'sta f:$00'+address,'sta a:$'+address)
    text=text[:begin]+block+text[end:]
    text=change(text,'pipe_fast_gate:\n','pipe_fast_gate:\n  phb\n  pea $0000\n  plb\n  plb\n')
    return change(text,'pipe_fast_unroll_end:\n  lda #0\n  tcd\n  rtl',
        'pipe_fast_unroll_end:\n  lda #0\n  tcd\n  plb\n  rtl')


def unroll(text,count):
    assert count in (16,20)
    text=change(text,'  cmp #73\n','  cmp #'+str(count*6+1)+'\n')
    text=change(text,'  lda #72\n','  lda #'+str(count*6)+'\n')
    begin=text.index('pipe_fast_unroll_start:\n')
    end=text.index('pipe_fast_unroll_end:\n',begin)
    block=text[begin:end]
    block=change(block,'.repeat 12, I','.repeat '+str(count)+', I')
    for old,new in ((72,count*6),(70,count*6-2),(68,count*6-4)):
        block=change(block,'pipe_records-'+str(old),'pipe_records-'+str(new))
    text=text[:begin]+block+text[end:]
    text=change(text,'=12*23','='+str(count)+'*23')
    return change(text,'.min(I,12)*23','.min(I,'+str(count)+')*23')
