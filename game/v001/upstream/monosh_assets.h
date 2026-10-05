#ifndef MSXSH_MONOSH_ASSETS_H
#define MSXSH_MONOSH_ASSETS_H

#include "mode3_sprite.h"

#ifdef __ROM__
#define MONOSH_ASSET_BANKED __banked
#else
#define MONOSH_ASSET_BANKED
#endif

typedef struct MonoshMode3Asset {
    Mode3PatternRef small;
    Mode3PatternRef wide_left;
    Mode3PatternRef wide_right;
    const unsigned char *small_pixels;
    const unsigned char *wide_pixels;
    const unsigned char *height_by_width;
    const unsigned char *width_by_depth;
} MonoshMode3Asset;

void monosh_asset_upload(const MonoshMode3Asset *asset);
void monosh_assets_upload_all(void) MONOSH_ASSET_BANKED;
void monosh_boss_bullet_asset_upload(void) MONOSH_ASSET_BANKED;
void monosh_bom_assets_upload_extra(void) MONOSH_ASSET_BANKED;
void monosh_em1_assets_upload_extra(void) MONOSH_ASSET_BANKED;
void monosh_title_draw(unsigned char visible) MONOSH_ASSET_BANKED;
extern unsigned char monosh_title_visible;
extern const MonoshMode3Asset monosh_asset_bush0;
extern const MonoshMode3Asset monosh_asset_bush1;
extern const MonoshMode3Asset monosh_asset_flystone;
extern const MonoshMode3Asset monosh_asset_em0;
extern const MonoshMode3Asset monosh_asset_tree0;
extern const MonoshMode3Asset monosh_asset_bom0;
extern const MonoshMode3Asset monosh_asset_ebullet0;
extern const MonoshMode3Asset monosh_asset_ebullet1;
extern const MonoshMode3Asset monosh_asset_ebullet2;
extern const MonoshMode3Asset monosh_asset_ebullet3;
extern const MonoshMode3Asset monosh_asset_em1_closed;
extern const MonoshMode3Asset monosh_asset_boss_body;
extern const MonoshMode3Asset monosh_asset_boss_face;

#endif
