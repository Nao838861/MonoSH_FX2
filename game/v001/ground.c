#include "port.h"
/* Ordinary BG3 + HDMAで横の市松と奥行きの帯を合成する。 */
unsigned char fx_ground_color1[3][150], fx_ground_color3[3][150];
unsigned char fx_ground_horizontal[3][270];
unsigned char *fx_ground_hptr;
unsigned char fx_ground_world_phase;
unsigned int fx_ground_palette_record;
unsigned char fx_ground_far_x[3][10];
unsigned char *fx_ground_far_xptr;
extern unsigned int fx_far_u_acc, fx_far_d_acc;
unsigned char *fx_ground_vptr, *fx_ground_c1ptr, *fx_ground_c3ptr;
unsigned int fx_ground_horizon;
int fx_ground_far_y;
/* 3組の表を切り替えるfx_build_groundと行別投影はground.s。 */
