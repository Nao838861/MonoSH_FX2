"""右端の行を後ろから調べ、短い可視prefixだけを命令コピーする。"""


def transform(text):
    text=text.replace('.import __RIGHTJIT_LOAD__, __RIGHTJIT_SIZE__\n','')
    a=text.index('sa1_right_clip_draw:\n');b=text.index('rightChain=$80\n',a)
    text=text[:a]+'sa1_right_clip_draw:\n  jml right_entry\n'+text[b:]
    a=text.index('right_new:\n');b=text.index('right_scanned:\n',a)
    text=text[:a]+'''right_new:
  ; rowcodeの直前2byteに長さ/extentがある。命令は全て3byte。
  lda rightCode
  sec
  sbc #2
  sta rightLength
  lda rightCode+2
  sta rightLength+2
  lda [rightLength]
  and #255
  sec
  sbc #4
  bmi right_empty
  tay
right_scan:
  lda [rightCode],y
  and #255
  cmp #$9d
  bne right_scan_previous
  iny
  lda [rightCode],y
  dey
  cmp rightLimit
  bcc right_scan_found
right_scan_previous:
  tya
  sec
  sbc #3
  bmi right_empty
  tay
  bra right_scan
right_scan_found:
  tya
  clc
  adc #3
  sta rightLength
  bra right_scanned
right_empty:
  stz rightLength
'''+text[b:]
    a=text.index('  jsl sa1_dma_try_begin\n',text.index('right_scanned:\n'))
    b=text.index('right_copy_cpu:\n',a)
    return text[:a]+text[b:]
