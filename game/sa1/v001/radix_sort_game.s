; 奥行き、priorityの順に安定bucketソートする。
; 一段目の出力にkeysを再利用し、二段目でorderへ戻す。
.setcpu "65816"
.smart
.macpack longbranch
.import order, keys, _fx_draw
.importzp packet_work
.export sa1_radix_sort
.segment "COLORBSS"
radix_heads: .res 512
radix_links: .res 128
.segment "CODE"
.macro radix_pass input, output, high
.local reset, link, scan, walk, scan_next
  lda #255
  sta packet_work+12
  stz packet_work+14
  ldy #0
reset:
  lda input,y
  tax
  lda _fx_draw+8,x
  .if high
    xba
  .else
    eor #255
  .endif
  and #255
  cmp packet_work+12
  bcs :+
  sta packet_work+12
:
  cmp packet_work+14
  bcc :+
  sta packet_work+14
:
  asl
  tax
  stz radix_heads,x
  iny
  iny
  cpy packet_work+8
  bcc reset
  ldy packet_work+8
  dey
  dey
link:
  lda input,y
  tax
  lda _fx_draw+8,x
  .if high
    xba
  .else
    eor #255
  .endif
  and #255
  asl
  tax
  lda radix_heads,x
  sta radix_links,y
  tya
  inc
  inc
  sta radix_heads,x
  dey
  dey
  bpl link
  stz packet_work+16
  lda packet_work+14
  inc
  asl
  sta packet_work+18
  lda packet_work+12
  asl
  tax
scan:
  lda radix_heads,x
  stz radix_heads,x
  beq scan_next
walk:
  dec
  dec
  tay
  lda input,y
  phy
  ldy packet_work+16
  sta output,y
  iny
  iny
  sty packet_work+16
  ply
  lda radix_links,y
  bne walk
scan_next:
  inx
  inx
  cpx packet_work+18
  bcc scan
.endmacro
sa1_radix_sort:
  rep #$30
  radix_pass order, keys, 0
  radix_pass keys, order, 1
  rts
