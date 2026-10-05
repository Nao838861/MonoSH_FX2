; 最大原画からの縮小。入力はCPUが投影・clip後に用意したGSUレジスタ。
; r1/r2=描画座標、r3=du(Q8.8)、r4=dv、r5=左端、r6=行数、
; r7=source V(Q8.8)、r9=出力幅、r10=source U開始値。
; 原画のROM pitchは256bytes、GSU r7=V・r8=UのMERGEを使う。
.include "casfx.inc"
.segment "GSU"
.export clear_entry, nearest_entry, nearest_unroll_entry, runs_entry, integer_entry
.export clear_stop, nearest_stop, nearest_unroll_stop, runs_stop, integer_stop
.export bounded_entry, bounded_stop
.export runs_copy_entry, runs_copy_stop, runs_half_entry, runs_half_stop
.export runs_quarter_entry, runs_quarter_stop
.export packed_copy_entry, packed_copy_stop, packed_half_entry, packed_half_stop
.export packed_quarter_entry, packed_quarter_stop

.align 16
clear_entry:
  cache
  sub r0
  iwt r1,#$2000
  iwt r12,#$1800
  iwt r13,#.loword(clear_loop)
clear_loop:
  stw (r1)
  inc r1
  loop
  inc r1
  iwt r11,#$0000
  ldw (r11)             ; 最後のRAM書き込みの完了を待つ
clear_stop:
  stop
  nop

.align 16
nearest_entry:
  ibt r0,#$41
  romb
  sub r0
  cmode                 ; 0を透明とする
  cache
  iwt r13,#.loword(nearest_pixel)
nearest_row:
  move r1,r5
  move r8,r10
  move r12,r9
nearest_pixel:
  merge r14
  with r8
  add r3                ; ROM読出待ちにU更新を重ねる
  getc                  ; 原画byteを直接COLORへ。GETB+COLORを省略
  loop
  plot                  ; branch delay slot。PLOTがXを増やす
  with r7
  add r4
  dec r6
  bne nearest_row
  inc r2
  rpix                  ; pixel cacheをflush
  iwt r11,#$0000
  ldw (r11)
nearest_stop:
  stop
  nop

; 8画素単位でloop費用を減らす。幅は8の倍数の測定用。
.align 16
nearest_unroll_entry:
  ibt r0,#$41
  romb
  sub r0
  cmode
  cache
  iwt r13,#.loword(unroll_pixels)
unroll_row:
  move r1,r5
  move r8,r10
  move r12,r9            ; この入口ではr9=幅/8
unroll_pixels:
  .repeat 8
    merge r14
    with r8
    add r3
    getc
    plot
  .endrepeat
  loop
  nop
  with r7
  add r4
  dec r6
  bne unroll_row
  inc r2
  rpix
  iwt r11,#$0000
  ldw (r11)
nearest_unroll_stop:
  stop
  nop

; 整数比縮小の専用経路。r3=整数のsource X増分、r10=source X開始。
; source Yは他経路と同じQ8.8。1:1/1:2/1:4などでMERGEとUの固定小数更新を省く。
.align 16
integer_entry:
  ibt r0,#$41
  romb
  sub r0
  cmode
  cache
  iwt r13,#.loword(integer_pixels)
  iwt r8,#$FF00
integer_row:
  move r1,r5
  move r12,r9
  from r7
  and r8
  to r14
  add r10
integer_pixels:
  getc
  with r14
  add r3
  loop
  plot
  with r7
  add r4
  dec r6
  bne integer_row
  inc r2
  rpix
  iwt r11,#$0000
  ldw (r11)
integer_stop:
  stop
  nop

; 原画各行の不透明区間の外側を飛ばす。内部の穴は点参照する。
; 端点を前後1画素広げ、Q8.8と厳密比率の丸め差で不透明画素を欠かさない。
.align 16
bounded_entry:
  sub r0
  cmode
  cache
  move r11,r6           ; rows
  move r6,r3            ; du / LMULTの乗数
  move r10,r4           ; dvをLMULTのlow出力から退避
  iwt r3,#$FF00
  iwt r13,#.loword(bounded_pixels)
bounded_row:
  ibt r0,#$43
  romb
  from r7
  to r14
  and r3
  getb
  inc r14
  umult r9
  ibt r4,#127
  add r4
  add r0
  hib
  beq bounded_start_zero
  nop
  dec r0
bounded_start_zero:
  move r8,r0
  to r1
  add r5
  getb
  umult r9
  add r4
  add r0
  hib
  inc r0
  cmp r9
  blt bounded_end_ok
  nop
  move r0,r9
bounded_end_ok:
  to r12
  sub r8
  from r8
  lmult
  move r8,r4
  ibt r0,#$41
  romb
bounded_pixels:
  merge r14
  with r8
  add r6
  getc
  loop
  plot
  with r7
  add r10
  dec r11
  bne bounded_row
  inc r2
  rpix
  iwt r3,#0
  ldw (r3)
bounded_stop:
  stop
  nop

; 各原画行の同色runを縮小。透明区間は走査しない。
; 原画幅128、各run=[start,end,color]、行pitch256、先頭byte=run数。
; endpoint=ceil(sourceX*出力幅/128)。UMULTで積を求め、(+127)*2のHIB。
; source画像は1枚の最大原画。横の縮小計算はGSUで行う。
.align 16
runs_entry:
  ibt r0,#$42
  romb
  sub r0
  cmode
  cache
  iwt r3,#$FF00
  iwt r10,#127
  iwt r13,#.loword(run_pixels)
runs_row:
  from r7
  to r14
  and r3
  getb r8
  inc r14
  from r8
  or r8
  beq runs_next_row
  nop
runs_next:
  getb
  inc r14
  umult r9
  add r10
  add r0
  hib
  to r1
  add r5
  getb
  inc r14
  umult r9
  add r10
  add r0
  hib
  add r5
  to r12
  sub r1
  getc
  inc r14
  from r12
  or r12
  beq run_finished
  nop
run_pixels:
  loop
  plot
run_finished:
  dec r8
  bne runs_next
  nop
runs_next_row:
  with r7
  add r4
  dec r6
  bne runs_row
  inc r2
  rpix
  iwt r11,#$0000
  ldw (r11)
runs_stop:
  stop
  nop

; 等倍・1/2・1/4の端点計算をシフトへ置換する。原画runデータは共通。
.macro RLE_SHIFT entryname, stopname, shift
  .local row, next, pixels, finished, nextrow
  .align 16
entryname:
  ibt r0,#$42
  romb
  sub r0
  cmode
  cache
  iwt r3,#$FF00
  iwt r13,#.loword(pixels)
row:
  from r7
  to r14
  and r3
  getb r8
  inc r14
  from r8
  or r8
  beq nextrow
  nop
next:
  getb
  inc r14
  .if shift > 0
    add #((1<<shift)-1)
    .repeat shift
      lsr
    .endrepeat
  .endif
  to r1
  add r5
  getb
  inc r14
  .if shift > 0
    add #((1<<shift)-1)
    .repeat shift
      lsr
    .endrepeat
  .endif
  add r5
  to r12
  sub r1
  getc
  inc r14
  from r12
  or r12
  beq finished
  nop
pixels:
  loop
  plot
finished:
  dec r8
  bne next
  nop
nextrow:
  with r7
  add r4
  dec r6
  bne row
  inc r2
  rpix
  iwt r11,#0
  ldw (r11)
stopname:
  stop
  nop
.endmacro

RLE_SHIFT runs_copy_entry, runs_copy_stop, 0
RLE_SHIFT runs_half_entry, runs_half_stop, 1
RLE_SHIFT runs_quarter_entry, runs_quarter_stop, 2

; 4texelを1byteにpackした原画。ROM待ちを4/2/1画素で共有する。
; 原画幅128、row pitch32bytes、低bitからcolorを格納。
; r9=出力幅/(4>>shift)、出力幅はグループサイズの倍数。
.macro PACKED_SHIFT entryname, stopname, shift
  .local row, pixels
  .align 16
entryname:
  ibt r0,#$44
  romb
  sub r0
  cmode
  cache
  iwt r8,#$FF00
  iwt r13,#.loword(pixels)
row:
  from r7
  and r8
  lsr
  lsr
  to r14
  lsr                   ; floor(sourceY)*32
  move r1,r5
  move r12,r9
pixels:
  getb
  inc r14               ; 次byteをprefetchし、色の展開とPLOTを重ねる
  .repeat (4>>shift), i
    color               ; 2bpp PLOTはCOLORの低2bitを使う
    .if i = (4>>shift)-1
      loop
      plot
    .else
      plot
      .repeat (2<<shift)
        lsr
      .endrepeat
    .endif
  .endrepeat
  with r7
  add r4
  dec r6
  bne row
  inc r2
  rpix
  iwt r11,#0
  ldw (r11)
stopname:
  stop
  nop
.endmacro

PACKED_SHIFT packed_copy_entry, packed_copy_stop, 0
PACKED_SHIFT packed_half_entry, packed_half_stop, 1
PACKED_SHIFT packed_quarter_entry, packed_quarter_stop, 2

.segment "PIXELS"
  .incbin "pixels.bin"
.segment "RUNS"
  .incbin "runs.bin"
.segment "BOUNDS"
  .incbin "bounds.bin"
.segment "PACKED"
  .incbin "packed.bin"
