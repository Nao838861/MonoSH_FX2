"""MonoSH FX2 の設計用帯域概算。エミュレータや実機の測定ではない。"""

import argparse
import math


MASTER_HZ = 21_477_272
LINE_CLOCKS = 1364
REFRESH_CLOCKS = 40
FRAME_LINES = 262
VBLANK_LINES = 37
NORMAL_HEIGHT = 224
DMA_CLOCKS_PER_BYTE = 8


def height_balance(height, baseline_bytes):
    """横256・2bpp。通常224行の転送枠を指定して黒帯の効果を比較する。"""
    image_bytes = 256 * height // 4
    added_bytes = (NORMAL_HEIGHT - height) * (LINE_CLOCKS - REFRESH_CLOCKS) / DMA_CLOCKS_PER_BYTE
    capacity = math.floor(baseline_bytes + added_bytes)
    return image_bytes, capacity, capacity - image_bytes


def estimate(width, height, commands, command_bytes, header_bytes, reserve_ms, display_height=None):
    framebuffer_bytes = width * height * 2 // 8
    packet_bytes = header_bytes + commands * command_bytes
    if display_height is None:
        display_height = height
    blank_lines = VBLANK_LINES + NORMAL_HEIGHT - display_height
    clocks_per_line_available = LINE_CLOCKS - REFRESH_CLOCKS
    blank_bytes = math.floor(blank_lines * clocks_per_line_available / DMA_CLOCKS_PER_BYTE)
    effective_bytes_per_ms = (
        MASTER_HZ / DMA_CLOCKS_PER_BYTE / 1000
        * clocks_per_line_available / LINE_CLOCKS
    )
    frame_ms = FRAME_LINES * LINE_CLOCKS / MASTER_HZ * 1000
    fb_dma_ms = framebuffer_bytes / effective_bytes_per_ms
    packet_dma_ms = packet_bytes / effective_bytes_per_ms
    render_ms = frame_ms - fb_dma_ms - packet_dma_ms - reserve_ms
    reserve_bytes = math.ceil(reserve_ms * effective_bytes_per_ms)
    # 描画リストの reverse DMA は表示中でも可能。ここでは同じ blank 窓へ
    # まとめる単純なスケジュールを、より厳しい条件として計算する。
    blank_margin = blank_bytes - framebuffer_bytes - packet_bytes - reserve_bytes
    return framebuffer_bytes, blank_bytes, fb_dma_ms, packet_dma_ms, render_ms, blank_margin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", type=int, default=64)
    parser.add_argument("--command-bytes", type=int, default=24)
    parser.add_argument("--header-bytes", type=int, default=32)
    parser.add_argument("--reserve-ms", type=float, default=0.3)
    parser.add_argument("--normal-dma-bytes", type=int, default=7168,
                        help="通常224行表示での仮定転送枠。既定7168は7KiBで、実測値ではない")
    args = parser.parse_args()
    if min(args.commands, args.command_bytes, args.header_bytes, args.reserve_ms) < 0:
        parser.error("各値は0以上にしてください")
    if args.normal_dma_bytes < 0:
        parser.error("--normal-dma-bytesは0以上にしてください")
    print("横256・2bppの画像だけの収支。1KiB=1024bytes、通常表示は224行。")
    print("通常枠を指定した仮定と、NTSC標準タイミング上限6123bytesを分けて表示する。")
    print(f"仮定通常枠={args.normal_dma_bytes}bytes。黒帯はforced blankでVRAM転送に使う。")
    print("高さ  画像KiB  仮定枠KiB  仮定余裕bytes  標準枠KiB  標準余裕bytes")
    for height in (224, 208, 200, 192, 184, 176, 160):
        fb, capacity, margin = height_balance(height, args.normal_dma_bytes)
        _, standard, standard_margin = height_balance(height, 6123)
        print(f"{height:>4}  {fb / 1024:>7.2f}  {capacity / 1024:>9.2f}  {margin:>13}  {standard / 1024:>9.2f}  {standard_margin:>13}")
    print("画像以外のVRAM/OAM/CGRAM更新と設定費用は別途必要。リストのRAM転送は表示中も可能。")
    print()
    print("設計概算。DRAM refreshを控除。HDMA・設定・OAM等はreserveに含める仮定。")
    print("CPU処理とGSU処理は並行する仮定。CPU処理時間はGSU時間から引いていない。")
    print("GSUの最大時間にはclear・cache fill・flush・STOPを含む。")
    print("描画領域 -> 表示領域       FB bytes  blank上限  FB DMA ms  list DMA ms  GSU最大ms  blank余裕bytes")
    cases = ((256, 224, 224), (256, 192, 192), (224, 192, 192),
             (256, 176, 176), (256, 160, 160), (224, 168, 168),
             (256, 96, 192), (256, 128, 128))
    for width, height, display_height in cases:
        values = estimate(width, height, args.commands, args.command_bytes, args.header_bytes, args.reserve_ms, display_height)
        fb, blank, fb_ms, packet_ms, render_ms, margin = values
        region = f"{width}x{height} -> {width}x{display_height}"
        print(f"{region:<24}  {fb:>8}  {blank:>9}  {fb_ms:>9.3f}  {packet_ms:>11.3f}  {render_ms:>9.3f}  {margin:>14}")
    print("blank余裕はリストもblank内へ置いた場合の値。画像だけの可否とは区別する。")
    print("256x176・224x168・256x96はGSUの格納領域から列ごとに転送。区間設定費用は要計測。")
    print("256x96 -> 256x192はBGの縦スクロールHDMAで行を2回ずつ表示する未検証案。")


if __name__ == "__main__":
    main()
