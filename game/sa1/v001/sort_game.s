; 深度・priorityを変えず、同じキーの元順序を保持するbucket sort。
; 画面用descriptorの$0400領域とは分離する。
.setcpu "65816"
.smart
.macpack longbranch
.import order, keys
.importzp packet_work
.export sa1_sort_packet
.segment "COLORBSS"
.res $200
sort_heads: .res 768*2
sort_stamps: .res 768
sort_links: .res 128
sort_values: .res 128
.segment "BSS"
sort_generation: .res 2
sort_min: .res 6
sort_max: .res 6
.segment "CODE"
snode=$0160
skey=$0162
spri=$0164
sout=$0166
slimit=$0168
sa1_sort_packet:
  rep #$30
  lda sort_generation
  beq sort_clear
  inc
  and #255
  bne sort_generation_ready
sort_clear:
  ldx #766
sort_clear_loop:
  stz sort_stamps,x
  dex
  dex
  bpl sort_clear_loop
  lda #1
sort_generation_ready:
  sta sort_generation
  ldx #4
  lda #$ffff
sort_init:
  sta sort_min,x
  stz sort_max,x
  dex
  dex
  bpl sort_init
  lda packet_work+8
  jeq sort_success
  dec
  dec
  sta snode
sort_node:
  ldx snode
  lda order,x
  sta sort_values,x
  lda keys,x
  cmp #768
  jcs sort_fallback
  sta skey
  xba
  and #255
  asl
  tax
  lda skey
  and #255
  cmp sort_min,x
  bcs :+
  sta sort_min,x
:
  cmp sort_max,x
  bcc :+
  sta sort_max,x
:
  ldx skey
  sep #$20
  lda sort_stamps,x
  cmp sort_generation
  beq sort_existing
  lda sort_generation
  sta sort_stamps,x
  rep #$20
  txa
  asl
  tax
  lda #$ffff
  sta sort_heads,x
  bra sort_link
sort_existing:
  rep #$20
  txa
  asl
  tax
sort_link:
  lda sort_heads,x
  ldy snode
  sta sort_links,y
  tya
  sta sort_heads,x
  dec snode
  dec snode
  jpl sort_node
  stz sout
  stz spri
sort_priority:
  ldx spri
  lda sort_min,x
  cmp #$ffff
  beq sort_next_priority
  sta skey
  lda sort_max,x
  sta slimit
  txa
  lsr
  xba
  clc
  adc skey
  sta skey
  txa
  lsr
  xba
  clc
  adc slimit
  sta slimit
sort_bucket:
  ldx skey
  sep #$20
  lda sort_stamps,x
  cmp sort_generation
  bne sort_next_bucket8
  rep #$20
  txa
  asl
  tax
  lda sort_heads,x
  tay
sort_output:
  ldx sout
  lda sort_values,y
  sta order,x
  inc sout
  inc sout
  lda sort_links,y
  tay
  bpl sort_output
  bra sort_next_bucket
sort_next_bucket8:
  rep #$20
sort_next_bucket:
  lda skey
  cmp slimit
  beq sort_next_priority
  inc skey
  bra sort_bucket
sort_next_priority:
  inc spri
  inc spri
  lda spri
  cmp #6
  bcc sort_priority
sort_success:
  sec
  rts
sort_fallback:
  clc
  rts
