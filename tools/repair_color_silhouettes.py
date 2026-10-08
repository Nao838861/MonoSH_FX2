"""Color the frozen sprite structure without replacing its pose or transparency.

Recorded video crops are hue/lightness references, not interchangeable animation
frames. The NES-derived opaque mask and dark details are the geometry authority.
This works from the checked-in crops and does not need the original video.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw
from import_recorded_bg_colors import PALETTES as RECORDED_PALETTES, quantize

PALETTES = [[color[:] for color in palette] for palette in RECORDED_PALETTES]
# The recording has warm-white cores and orange midtones, not solid lemon
# yellow. Preserve the dark outline contrast while restoring the pale core.
PALETTES[4] = [[0,0,0],[15,1,0],[31,15,3],[31,30,26]]
# Palette 0 belongs to the enemy lens/metal. The shadow shares grass palette 1.
# The title uses the
# existing near-white palette 3 so gray enemy metal cannot gray the banner.
# Put the red lens in pixels, never in a separate red 8x8 attribute block.
PALETTES[0][2] = [31,3,2]
PALETTES[0][3] = [22,23,25]
# One palette per tree/boss prevents source-cell and scaled-screen seams.
PALETTES[2] = [[0,0,0],[1,7,2],[3,21,4],[22,14,10]]
PALETTES[7] = [[0,0,0],[1,7,2],[7,23,6],[25,25,20]]

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'game/v001/assets'
DEST = ASSETS / 'bg_color'
RECORDED = [0, 1, 2, 3, 4, 6, 7, 8, 11, 12, 13, 14, 31]
POLICIES = {0:[1], 1:[1], 2:[3], 3:[0], 4:[2], 6:[6], 7:[5],
            8:[4], 11:[3], 12:[3], 13:[2], 14:[7], 31:[4], 37:[6]}
GRAY = [0,0,0,24,24,24,132,132,132,255,255,255] + [0]*756
RGB = np.array(PALETTES, dtype=float) * 255 / 31


def enemy_lens_mask(original):
    """Reviewed red interior of source 03, with the white glint and dark rim.

    Only the top central lens may recolor original dark pixels. Its highlight
    component is still white, and one pixel of the original rim stays dark.
    The fixed source-coordinate mask is independently stored and regression
    checked; it never depends on a source attribute cell or screen alignment.
    """
    opaque = original[:,:,3] >= 128
    light = original[:,:,:3].astype(int).sum(axis=2) >= 384
    yy,xx = np.indices(opaque.shape)
    glint = light & (xx >= 24) & (xx < 29) & (yy >= 2) & (yy < 12)
    lens = opaque & (~light | glint) & (xx >= 22) & (xx < 34) & (yy >= 1) & (yy < 14)
    padded = np.pad(lens,1)
    interior = lens & padded[:-2,1:-1] & padded[2:,1:-1] & padded[1:-1,:-2] & padded[1:-1,2:]
    return interior & ~light


def structure_color(asset):
    base = np.array(Image.open(ASSETS/f'{asset:02d}.png').convert('RGBA'))
    opaque = base[:,:,3] >= 128
    light = base[:,:,:3].astype(int).sum(axis=2) >= 384
    ref_path = DEST/f'{asset:02d}_source.png'
    reference = np.array(Image.open(ref_path).convert('RGBA').resize(
        (base.shape[1],base.shape[0]),Image.Resampling.NEAREST)) if ref_path.exists() else None
    indices = np.where(opaque, np.where(light,3,1),0).astype(np.uint8)
    # These regions are anchored to the frozen source drawing, never to a
    # resized recording or to an 8x8 attribute-cell boundary.
    yy,xx = np.indices(opaque.shape)
    if asset == 4:
        indices[opaque & light] = 2
        trunk = (yy >= 69) | ((yy >= 64) & (xx >= 14) & (xx <= 21))
        indices[opaque & light & trunk] = 3
    elif asset in [13,14]:
        indices[opaque & light] = 2
        if asset == 13:
            belly = (yy >= 48) & (xx >= 24) & (xx < 105)
            indices[opaque & light & belly] = 3
        if asset == 14:
            eyes = ((xx >= 24) & (xx < 36) & (yy >= 37) & (yy < 51)) | ((xx >= 53) & (xx < 67) & (yy >= 37) & (yy < 48))
            horns = ((xx >= 13) & (xx < 29) & (yy < 22)) | ((xx >= 41) & (xx < 65) & (yy < 14)) | ((xx >= 66) & (yy < 21))
            indices[opaque & light & (eyes | horns)] = 3
    elif asset == 3:
        indices[enemy_lens_mask(base)] = 2
    cells = np.full((16,16),15,dtype=np.uint8)
    preview = np.zeros(base.shape,dtype=np.uint8)
    for ty in range((base.shape[0]+7)//8):
        for tx in range((base.shape[1]+7)//8):
            sl = np.s_[ty*8:(ty+1)*8,tx*8:(tx+1)*8]
            mask = opaque[sl]
            # Tile centers can sample a transparent source cell while the
            # same screen tile contains an opaque edge. Every asset now uses
            # one palette, so cover the full source rectangle consistently.
            choices = POLICIES[asset]
            pal = choices[0]
            if reference is not None and asset not in [3,4,13,14]:
                src = reference[sl][:,:,:3].astype(float)
                observed = (reference[sl][:,:,3] >= 128) & mask
                if observed.any():
                    errors = ((src[:,:,None,None,:]-RGB[None,None,:,1:,:])**2).sum(axis=-1)
                    pal = min(choices,key=lambda p:float(errors[:,:,p,:].min(axis=-1)[observed].sum()))
                    # Only split old highlights into mid/light. Never erase an
                    # outline, silhouette pixel or dark feature for video RGB.
                    nearest = ((src[:,:,None,:]-RGB[pal,None,None,2:,:])**2).sum(axis=-1).argmin(axis=-1)+2
                    # These captures are different rotations/open states.
                    # Their spatial shading must not cross the frozen pose.
                    use = observed & light[sl] if asset not in [6,7,8,11,12] else np.zeros(mask.shape,dtype=bool)
                    indices[sl][use] = nearest[use]
            cells[ty,tx] = pal
            preview[sl][:,:,:3] = np.rint(RGB[pal,indices[sl]]).astype(np.uint8)
            preview[sl][:,:,3] = mask*255
    indexed = Image.fromarray(indices).convert('P'); indexed.putpalette(GRAY)
    indexed.info['transparency'] = 0
    return indexed, Image.fromarray(preview), cells


def imported_indices(asset):
    """Reproduce the flawed historical import, for stable before/after metrics."""
    base = Image.open(ASSETS/f'{asset:02d}.png').convert('RGBA')
    if asset == 37:
        a=np.array(base);return np.where(a[:,:,3]<128,0,np.where(a[:,:,:3].astype(int).sum(axis=2)>=384,3,1)).astype(np.uint8)
    source=json.loads((DEST/'source.json').read_text())['assets'][str(asset)]
    im=Image.open(DEST/f'{asset:02d}_source.png').convert('RGBA').resize(base.size,Image.Resampling.NEAREST)
    if source['original_outline_matte']:
        a=np.array(im);a[:,:,3]=np.minimum(a[:,:,3],np.array(base)[:,:,3]);im=Image.fromarray(a)
    return np.array(quantize(im,source['palettes'])[0])


def main():
    allcells = np.full((44,16,16),15,dtype=np.uint8)
    metrics = {}
    for asset in range(44):
        path = DEST/f'{asset:02d}.png'
        if not path.exists(): continue
        old = imported_indices(asset) if asset in POLICIES else np.array(Image.open(path))
        original = np.array(Image.open(ASSETS/f'{asset:02d}.png').convert('RGBA'))
        mask = original[:,:,3]>=128
        if asset in POLICIES:
            indexed,colored,cells = structure_color(asset)
            indexed.save(path,transparency=0); colored.save(DEST/f'{asset:02d}_color.png')
            allcells[asset] = cells
        else:
            indices = np.array(Image.open(path))
            pal = 1 if asset == 38 else 4 if asset in [5,39,40,41] else 3 if asset in [*range(32,37),42] else 0
            if asset == 38:
                # 草と重なる8x8属性セルでも、影は草の最暗色(index1)を使う。
                assert np.all(indices[mask] == 1),'shadow must use grass darkest index'
            for ty in range((indices.shape[0]+7)//8):
                for tx in range((indices.shape[1]+7)//8):
                    allcells[asset,ty,tx]=pal
        new = np.array(Image.open(path))
        assert np.array_equal(new!=0,mask),(asset,'silhouette')
        dark = mask & (original[:,:,:3].astype(int).sum(axis=2)<384)
        protected_dark = dark & ~enemy_lens_mask(original) if asset == 3 else dark
        assert np.all(new[protected_dark]==1),(asset,'dark structure')
        if asset in POLICIES:
            union = mask | (old!=0)
            metrics[str(asset)] = {'opaque_pixels':int(mask.sum()),'repaired_mask_errors':int(np.count_nonzero((old!=0)!=mask)),
                'before_mask_iou':float(np.count_nonzero(mask & (old!=0))/np.count_nonzero(union)),
                'after_mask_iou':1.0,'dark_structure_preserved_outside_reviewed_eye':True,
                'intentional_dark_lens_pixels':int(enemy_lens_mask(original).sum()) if asset == 3 else 0,
                'palette_candidates':POLICIES[asset]}
    compact=bytearray();offsets=bytearray()
    for asset in range(44):
        offsets.extend(len(compact).to_bytes(2,'little'))
        path=DEST/f'{asset:02d}.png'; rows=(Image.open(path).height+7)//8 if path.exists() else 0
        data=allcells[asset,:rows,:].flatten()
        compact.extend(int(data[i])|int(data[i+1])<<4 for i in range(0,len(data),2))
    (DEST/'cells.bin').write_bytes(compact);(DEST/'offsets.bin').write_bytes(offsets)
    palette = b''.join((r | g<<5 | b<<10).to_bytes(2,'little') for p in PALETTES for r,g,b in p)
    (DEST/'palette.bin').write_bytes(palette)
    manifest = {'method':'original alpha and structural detail; tree dark-green/green/brown; enemy red lens/gray metal; boss brown body and ivory eye/horn head',
        'reference':'source.json and frozen source PNGs remain unchanged; no unmasked original video is available here',
        'projectile37':'fourth rotation was accidentally grayscale; uses observed purple family from frame 6; exact arcade phase color remains unverified',
        'playerShadow':{'asset':38,'palette':1,'opaqueIndex':1,'sharesWithGrassAssets':[0,1]},
        'rgb5':PALETTES,'assets':metrics}
    (DEST/'silhouette_repair.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sheet=Image.new('RGB',(900,len(POLICIES)*160),(44,40,50));draw=ImageDraw.Draw(sheet)
    for row,asset in enumerate(POLICIES):
        draw.text((8,row*160+4),f'{asset:02d}  frozen monochrome / recorded reference (may differ in pose) / repaired color',fill='white')
        for col,path in enumerate([ASSETS/f'{asset:02d}.png',DEST/f'{asset:02d}_source.png',DEST/f'{asset:02d}_color.png']):
            if not path.exists():continue
            im=Image.open(path).convert('RGBA');scale=min(270/im.width,130/im.height)
            im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.NEAREST)
            sheet.paste(im,(col*300+10,row*160+25),im)
    sheet.save(DEST/'comparison.png')
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
