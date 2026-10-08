#ifndef MONOSH_FX_PORT_H
#define MONOSH_FX_PORT_H
#include "monosh_draw.h"
#define FX_DRAW_MAX 64
typedef struct FxDraw {
    int x, bottom;
    unsigned char width, height, asset, flags, z, priority;
} FxDraw;
typedef struct FxCommand {
    unsigned int x, y, du, dv, left, height, v0, width, u0, bank;
} FxCommand;
/* fx_packetは最大20byte/要素の保存領域。FX_GSU_CLIPではFxDrawを10byteで
 * 詰めて送る。FX_GSU_UVのみなら20byteで寸法・clip量、CPU版はQ8.8 UV。 */
extern FxDraw fx_draw[FX_DRAW_MAX];
extern unsigned char fx_draw_count;
extern unsigned int fx_packet_count;
extern FxCommand fx_packet[FX_DRAW_MAX];
extern unsigned char fx_ground_phase;
extern unsigned int fx_buttons;
extern unsigned char fx_input, fx_fire_actions;
extern unsigned char monosh_runtime_fire_actions;
extern signed char monosh_ground_screen_delta;
extern unsigned char monosh_ground_offset;
extern const unsigned char fx_asset_width[], fx_asset_height[], fx_asset_bank[];
extern const unsigned int * const fx_du_table[], * const fx_dv_table[];
void fx_submit(int x, int bottom, unsigned char width, unsigned char height,
               unsigned char asset, unsigned char flags, unsigned char z,
               unsigned char priority);
void fx_build_packet(void);
void fx_toggle_color(void);
void fx_init(void);
void fx_frame(void);
void fx_present(void);
void fx_read_input(void);
void fx_build_ground(void);
void fx_send_ground(void);
void fx_enemy_em1_update(void *enemy, unsigned char slot);
void monosh_boss_render_only(void);
#endif
