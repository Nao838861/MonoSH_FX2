; 同priorityだけを安定にZ降順へ並べる。元FxDrawもpacket ABIも変更しない。
; headsは今回存在するkeyだけ初期化。256 bucket全消去は不要。
; 元順序を逆にたどって先頭へ挿入するので同じZの描画順も保存される。
.export bucket_sort, bucket_scan, bucket_copy
bucket_record:
  pha
  and #$ff00
  cpy #0
  bne bucket_priority
  sta $0160
  pla
  and #$ff
  sta $0164
  sta $0166
  bra bucket_reset
bucket_priority:
  cmp $0160
  beq :+
  inc $0162
:
  pla
  and #$ff
  cmp $0164
  bcs :+
  sta $0164
:
  cmp $0166
  bcc bucket_reset
  sta $0166
bucket_reset:
  asl
  phx
  tax
  stz bucket_heads,x
  plx
  rts
bucket_sort:
  ldy packet_work+8
  dey
  dey
bucket_link:
  lda keys,y
  and #$ff
  asl
  tax
  lda bucket_heads,x
  sta bucket_links,y
  tya
  inc
  inc
  sta bucket_heads,x
  dey
  dey
  bpl bucket_link
  stz $016a
  lda $0166
  inc
  asl
  sta $0168
  lda $0164
  asl
  tax
bucket_scan:
  lda bucket_heads,x
  stz bucket_heads,x       ; 次のfieldで存在しないkeyも空にしておく。STZはZを変えない。
  beq bucket_next
bucket_walk:
  dec
  dec
  tay
  lda order,y
  phy
  ldy $016a
  sta keys,y
  iny
  iny
  sty $016a
  ply
  lda bucket_links,y
  bne bucket_walk
bucket_next:
  inx
  inx
  cpx $0168
  bcc bucket_scan
  ldx #0
bucket_copy:
  lda keys,x
  sta order,x
  inx
  inx
  cpx packet_work+8
  bcc bucket_copy
  jmp sorted
