; 描画順がほぼ逆順でも配列を毎回ずらさない、安定した連結リスト挿入ソート。
.setcpu "65816"
.smart
.macpack longbranch
.import order, keys
.importzp packet_work
.export sa1_list_sort
.segment "COLORBSS"
list_links: .res 128
list_head: .res 2
list_tail: .res 2
list_index: .res 2
list_key: .res 2
.segment "CODE"
sa1_list_sort:
  rep #$30
  stz list_head
  stz list_tail
  lda #$ffff
  sta list_links
  lda #2
  sta list_index
list_insert:
  ldy list_index
  lda keys,y
  sta list_key
  ldx list_tail
  cmp keys,x
  bcs list_append
  ldx list_head
  cmp keys,x
  bcc list_prepend
list_search:
  lda list_links,x
  tay
  lda keys,y
  cmp list_key
  bcc list_advance
  beq list_advance
  tya
  ldy list_index
  sta list_links,y
  tya
  sta list_links,x
  bra list_next
list_advance:
  tyx
  bra list_search
list_prepend:
  txa
  sta list_links,y
  tya
  sta list_head
  bra list_next
list_append:
  tya
  sta list_links,x
  sta list_tail
  lda #$ffff
  sta list_links,y
list_next:
  inc list_index
  inc list_index
  lda list_index
  cmp packet_work+8
  bcc list_insert
  ldx list_head
  ldy #0
list_emit:
  lda order,x
  sta keys,y
  iny
  iny
  lda list_links,x
  tax
  cmp #$ffff
  bne list_emit
  ldx #0
list_copy:
  lda keys,x
  sta order,x
  inx
  inx
  cpx packet_work+8
  bcc list_copy
  rts
