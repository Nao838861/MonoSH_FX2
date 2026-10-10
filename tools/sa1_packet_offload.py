"""描画命令の安定ソートと変換だけをSA-1へ移す。ゲーム状態はS-CPUに維持する。"""
import re


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def packet(text,sort,objects,iram=False,arrays=False):
    text=change(text,'.import _fx_draw, _fx_draw_count, _fx_packet, _fx_packet_count',
                '_fx_draw=$1000\n_fx_draw_count=$1404\n_fx_packet=$0000\n_fx_packet_count=$1402')
    text=change(text,'.import _monosh_runtime_frame_counter','_monosh_runtime_frame_counter=$1400')
    text=change(text,'.import fx_reset_next_bounds, fx_add_next_bounds','')
    text=change(text,'.import fx_is_obj, fx_build_obj','')
    begin=text.index('.segment "ZEROPAGE"\n');end=text.index('.ifdef FX_BUCKET_SORT\n',begin)
    text=text[:begin]+'''dp=$00
pp=$02
steps=$04
packet_work=$06
order=$1300
keys=$1380
'''+text[end:]
    text=change(text,'  jsr fx_build_obj\n  jsr fx_reset_next_bounds\n','')
    text=change(text,'  sty packet_work+8                ; FXへ送る分だけをソート。論理draw自体は保存。',
                '  sty packet_work+8\n  cpy #24\n  bcc :+\n  jsr sa1_list_sort\n  jmp sorted\n:')
    text=change(text,'  plp\n  rts\n','  plp\n  rtl\n')
    text=text.replace('_fx_build_packet','sa1_packet_build')
    text=text.replace('.export sa1_packet_build','.export sa1_packet_build: far')
    text=text.replace('.segment "CODE"','.segment "GSU"').replace('.segment "RODATA"','.segment "GSU"')
    text=text.replace('  lda color_bullet_dimensions,x','  lda f:color_bullet_dimensions,x')
    # 元のCPU scratch $01xxはDBR=$43で出力packetと重なるため専用領域へ移す。
    text=re.sub(r'\$01([0-9a-fA-F]{2})',lambda m:'$15'+m[1],text)
    sort=sort.replace('.import order, keys\n','').replace('.importzp packet_work\n','')
    sort=sort.replace('.macpack longbranch\n','')
    begin=sort.index('.segment "COLORBSS"\n');end=sort.index('.segment "CODE"\n',begin)
    sort=sort[:begin]+'''list_links=$1420
list_head=$14a0
list_tail=$14a2
list_index=$14a4
list_key=$14a6
'''+sort[end:]
    sort=sort.replace('.segment "CODE"','.segment "GSU"')
    helper=objects[objects.index('fx_is_obj:\n'):objects.index('fx_build_obj:\n')]
    text=text.replace('fx_is_obj','sap_is_obj')
    helper=helper.replace('fx_is_obj','sap_is_obj')
    hot=text+'\n'+sort+'\n.segment "GSU"\n'+helper
    if arrays:
        hot=change(hot,'order=$1300\nkeys=$1380\n','')
        hot=change(hot,'list_links=$1420\nlist_head=$14a0\nlist_tail=$14a2\nlist_index=$14a4\nlist_key=$14a6\n','')
        begin=hot.index('initialize_order:\n');end=hot.index('initialized:\n',begin)
        hot=hot[:begin]+hot[begin:end].replace('lda _fx_draw','lda f:$430000+_fx_draw')+hot[end:]
        hot=change(hot,'  lda _fx_draw_count\n','  lda f:$430000+_fx_draw_count\n')
        hot=change(hot,'sorted:\n','sorted:\n  sep #$20\n  lda #$43\n  pha\n  plb\n  rep #$30\n')
        hot=hot.replace('  lda order,y\n  tax\n','  tyx\n  lda f:order,x\n  tax\n')
        begin=hot.index('sap_is_obj:\n')
        hot=hot[:begin]+hot[begin:].replace('lda _fx_draw','lda f:$430000+_fx_draw')
        hot+='\norder: .res 128\nkeys: .res 128\nlist_links: .res 128\nlist_head: .res 2\nlist_tail: .res 2\nlist_index: .res 2\nlist_key: .res 2\n'
    if iram:hot=hot.replace('.segment "GSU"','.segment "PACKETJIT"')
    wrapper='''
.segment "GSU"
.export sa1_packet_prepare: far, sa1_packet_finished: far
sa1_packet_prepare:
  rep #$30
  phd
  phb
  lda #$0700
  tcd
  sep #$20
  lda #$43
  pha
  plb
  rep #$30
  lda f:$000106
  sta $1404
  lda f:$0001a8
  sta $1400
  jsl sa1_packet_build
sa1_packet_finished:
  rep #$30
  lda $1402
  sta f:$000106
  plb
  pld
  rtl
'''
    if iram:
        wrapper=change(wrapper,'  rep #$30\n  phd\n', '''  rep #$30
  jsl sa1_dma_try_begin
  bcc sap_load_cpu
  lda #__PACKETJIT_SIZE__
  sta $2238
  lda #.loword(__PACKETJIT_LOAD__)
  sta $2232
  sep #$20
  lda #^__PACKETJIT_LOAD__
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0300
  sta $2235
  jsl sa1_dma_end
  bra sap_load_done
sap_load_cpu:
  phb
  ldx #.loword(__PACKETJIT_LOAD__)
  ldy #$0300
  lda #__PACKETJIT_SIZE__-1
  mvn #^__PACKETJIT_LOAD__,#$00
  plb
sap_load_done:
  phd
''')
        wrapper='.import __PACKETJIT_LOAD__, __PACKETJIT_SIZE__\n.import sa1_dma_try_begin: far, sa1_dma_end: far\n'+wrapper
    if arrays:
        wrapper=change(wrapper,'  lda #$43\n  pha\n  plb\n','  lda #$00\n  pha\n  plb\n')
        wrapper=wrapper.replace('  sta $1404\n','  sta f:$431404\n').replace('  sta $1400\n','  sta f:$431400\n')
    return hot+wrapper


def pipeline(text):
    text='.import packet_count_collect: far\n.import _monosh_runtime_frame_counter, _fx_draw\n'+text
    text=change(text,'pipe_collect_adaptive:\n','  jsl packet_count_collect\npipe_collect_adaptive:\n')
    text=change(text,'  lda #_fx_packet\n  sta f:$002181','  lda #_fx_draw\n  sta f:$002181')
    text=change(text,'  lda #0\n  sta f:$004302\n  sep #$20\n  sta f:$002183',
                '  lda #$1000\n  sta f:$004302\n  sep #$20\n  lda #0\n  sta f:$002183')
    return change(text,'render_started:\n  lda #1\n',
                  'render_started:\n  lda _monosh_runtime_frame_counter\n  sta f:$0031a8\n  lda #1\n')


def renderer(text):
    text='.setcpu "65816"\n.import sa1_packet_prepare: far\n'+text
    return change(text,'  jsl sa1_plan_dirty\n','  jsl sa1_packet_prepare\n  jsl sa1_plan_dirty\n')
