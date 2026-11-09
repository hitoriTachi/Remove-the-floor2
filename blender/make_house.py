"""Особняк по референсу. Запуск: python make_house.py (модуль bpy) или blender -b -P make_house.py
Ось -Y — фасад. 1 единица Blender = 1 метр. Результат: house.blend, house.glb, house.fbx, preview_*.png"""
import bpy, math, random, os, sys

OUT = os.path.dirname(os.path.abspath(__file__))
random.seed(7)
bpy.ops.wm.read_factory_settings(use_empty=True)
col = bpy.data.collections.new("House")
bpy.context.scene.collection.children.link(col)


def mat(name, rgb, rough=0.8, metal=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.blend_method = "BLEND"
    return m


STONE = mat("Stone", (0.62, 0.52, 0.36), 0.95)
TRIM = mat("WhiteTrim", (0.92, 0.9, 0.84), 0.6)
ROOF = mat("Roof", (0.12, 0.08, 0.06), 0.9)
BRICK = mat("Brick", (0.45, 0.2, 0.13), 0.9)
GLASS = mat("Glass", (0.55, 0.7, 0.8), 0.05, 0.0, 0.5)
DARKGLASS = mat("WindowDark", (0.12, 0.16, 0.2), 0.1)
DOOR = mat("Door", (0.22, 0.09, 0.05), 0.5)
IVY = mat("Ivy", (0.1, 0.32, 0.08), 0.9)
LEAF = mat("Hedge", (0.08, 0.26, 0.08), 0.9)
CYP = mat("Cypress", (0.05, 0.2, 0.08), 0.9)
FLOWER = mat("Flowers", (0.95, 0.95, 0.92), 0.8)
PAVE = mat("Paving", (0.72, 0.65, 0.52), 0.9)
PAVE2 = mat("Paving2", (0.6, 0.54, 0.43), 0.9)
GRASS = mat("Grass", (0.25, 0.45, 0.15), 1)
WATER = mat("Water", (0.2, 0.75, 0.8), 0.05)
GRAVEL = mat("Gravel", (0.7, 0.62, 0.5), 1)
BLACK = mat("Black", (0.02, 0.02, 0.02), 0.5)
IRON = mat("Iron", (0.03, 0.03, 0.03), 0.4, 0.8)


def put(obj, m):
    obj.data.materials.append(m)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col.objects.link(obj)
    return obj


def box(name, c, s, m):
    bpy.ops.mesh.primitive_cube_add(location=c)
    o = bpy.context.object
    o.name = name
    o.scale = (s[0] / 2, s[1] / 2, s[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    return put(o, m)


def cyl(name, c, r, h, m, v=24, r2=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(vertices=v, radius=r, depth=h, location=c)
    else:
        bpy.ops.mesh.primitive_cone_add(vertices=v, radius1=r, radius2=r2, depth=h, location=c)
    o = bpy.context.object
    o.name = name
    return put(o, m)


def sphere(name, c, s, m, seg=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, location=c)
    o = bpy.context.object
    o.name = name
    o.scale = s
    return put(o, m)


def mesh(name, verts, faces, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    o.data.materials.append(m)
    for p in me.polygons:
        p.use_smooth = False
    return o


def gable(name, x0, x1, y0, y1, z, h, axis, m, over=0.0):
    """Двускатная крыша; axis='x' — конёк вдоль X, 'y' — вдоль Y."""
    x0 -= over; x1 += over; y0 -= over; y1 += over
    if axis == "x":
        ym = (y0 + y1) / 2
        v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), (x0, ym, z + h), (x1, ym, z + h)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5)]
    else:
        xm = (x0 + x1) / 2
        v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), (xm, y0, z + h), (xm, y1, z + h)]
        f = [(0, 4, 5, 3), (1, 2, 5, 4), (0, 1, 4), (2, 3, 5)]
    return mesh(name, v, f, m)


def hip(name, x0, x1, y0, y1, z, h, ridge_inset, m, over=0.0):
    x0 -= over; x1 += over; y0 -= over; y1 += over
    ym = (y0 + y1) / 2
    r0, r1 = x0 + ridge_inset, x1 - ridge_inset
    v = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), (r0, ym, z + h), (r1, ym, z + h)]
    f = [(0, 1, 5, 4), (2, 3, 4, 5), (3, 0, 4), (1, 2, 5)]
    return mesh(name, v, f, m)


def window(cx, y, z, w=1.0, h=1.7, face=-1, name="Win", bars=True, stone_side="y"):
    """Окно на стене, перпендикулярной Y (face=-1 фасад, +1 тыл) или X (stone_side='x')."""
    d = 0.08
    if stone_side == "y":
        pos = lambda dx, dz, depth: (cx + dx, y + face * depth, z + dz)
        sz = lambda a, b, c: (a, b, c)
    else:
        pos = lambda dx, dz, depth: (y + face * depth, cx + dx, z + dz)
        sz = lambda a, b, c: (c, a, b)
    box(name + "_frame", pos(0, 0, d / 2), sz(w + 0.3, d, h + 0.3), TRIM)
    box(name + "_glass", pos(0, 0, d + 0.01), sz(w, 0.04, h), DARKGLASS)
    if bars:
        for i in (-1, 0, 1):
            box(name + "_vbar", pos(i * w / 3 * (1 if i else 0), 0, d + 0.05), sz(0.05, 0.05, h), TRIM)
        for j in range(-2, 3):
            box(name + "_hbar", pos(0, j * h / 5 * 0.9, d + 0.05), sz(w, 0.05, 0.05), TRIM)
    box(name + "_sill", pos(0, -h / 2 - 0.18, 0.12), sz(w + 0.5, 0.2, 0.1), TRIM)
    box(name + "_lintel", pos(0, h / 2 + 0.2, 0.1), sz(w + 0.5, 0.2, 0.2), TRIM)


def balustrade(name, x0, x1, y, z, h=0.9, axis="x"):
    n = max(2, int(abs(x1 - x0) / 0.28))
    for i in range(n + 1):
        t = x0 + (x1 - x0) * i / n
        p = (t, y, z + h / 2) if axis == "x" else (y, t, z + h / 2)
        cyl(name + "_baluster", p, 0.045, h * 0.85, TRIM, 8, 0.04)
    p = ((x0 + x1) / 2, y, z + h) if axis == "x" else (y, (x0 + x1) / 2, z + h)
    sz = (abs(x1 - x0) + 0.15, 0.2, 0.08) if axis == "x" else (0.2, abs(x1 - x0) + 0.15, 0.08)
    box(name + "_rail", p, sz, TRIM)
    p = ((x0 + x1) / 2, y, z + 0.04) if axis == "x" else (y, (x0 + x1) / 2, z + 0.04)
    box(name + "_base", p, sz, TRIM)


def chimney(name, x, y, z0, z1):
    box(name, (x, y, (z0 + z1) / 2), (0.9, 1.2, z1 - z0), BRICK)
    box(name + "_cap", (x, y, z1 + 0.06), (1.1, 1.4, 0.14), TRIM)
    for dx in (-0.2, 0.2):
        cyl(name + "_pot", (x + dx, y, z1 + 0.35), 0.13, 0.5, BRICK, 12)


def ivy(name, cx, y, z0, z1, w, face=-1, n=60, side="y"):
    for _ in range(n):
        u = random.uniform(-w / 2, w / 2)
        z = random.uniform(z0, z1)
        s = random.uniform(0.18, 0.4)
        p = (cx + u, y + face * 0.12, z) if side == "y" else (y + face * 0.12, cx + u, z)
        sphere(name, p, (s, s * 0.6, s) if side == "y" else (s * 0.6, s, s), IVY, 6)


def cypress(name, x, y, h=6, r=0.9):
    cyl(name + "_trunk", (x, y, 0.3), 0.12, 0.6, DOOR, 8)
    for i, (f, hh) in enumerate([(1.0, 0.45), (0.85, 0.4), (0.6, 0.35), (0.35, 0.3)]):
        cyl(name, (x, y, 0.5 + h * (0.3 + i * 0.22)), r * f, h * hh, CYP, 12, r * f * 0.35)


def hedge(name, c, s):
    box(name, c, s, LEAF)


def bush_flowers(name, x, y, n=18, spread=1.2):
    sphere(name + "_bush", (x, y, 0.4), (spread, spread * 0.8, 0.55), LEAF, 10)
    for _ in range(n):
        a = random.uniform(0, 6.28)
        r = random.uniform(0, spread * 0.9)
        sphere(name + "_bloom", (x + math.cos(a) * r, y + math.sin(a) * r * 0.8, random.uniform(0.5, 0.95)),
               (0.14, 0.14, 0.12), FLOWER, 6)


# ----------------------------------------------------------- фундамент и стены
H1, H2 = 3.3, 3.1      # высоты этажей
ZB = 0.5               # цоколь
ZT = ZB + H1 + H2      # верх стен
WALL = ZT

box("Plinth", (0, 0, ZB / 2), (22.4, 9.4, ZB), TRIM)
box("Main_body", (0, 0, ZB + (ZT - ZB) / 2), (22, 9, ZT - ZB), STONE)
# боковые крылья глубже назад (L-образный намёк, как на втором фото)
box("Wing_back_L", (-8, 6.5, ZB + (ZT - ZB - 0.6) / 2), (7, 6, ZT - ZB - 0.6), STONE)
box("Wing_back_R", (8, 6.5, ZB + (ZT - ZB - 0.6) / 2), (7, 6, ZT - ZB - 0.6), STONE)

# выступающие фронтонные эркеры: центр и два боковых
BAYS = [(-8.0, 5.0, "L"), (0.0, 5.4, "C"), (8.0, 5.0, "R")]
for bx, bw, tag in BAYS:
    pr = 1.6 if tag == "C" else 1.2
    zc = ZB + (ZT - ZB) / 2
    box(f"Bay_{tag}", (bx, -4.5 - pr / 2 + 0.5, zc), (bw, pr + 0.0, ZT - ZB), STONE)
    yf = -4.5 - pr + 0.5 + 0.0        # передняя плоскость эркера
    # угловые белые пилястры
    for sx in (-1, 1):
        box(f"Quoin_{tag}", (bx + sx * (bw / 2 - 0.1), yf - 0.04, zc), (0.28, 0.12, ZT - ZB), TRIM)
    # карниз
    box(f"Cornice_{tag}", (bx, yf - 0.1, ZT - 0.05), (bw + 0.5, pr + 0.4 + 0.2, 0.25), TRIM)
    box(f"Belt_{tag}", (bx, yf - 0.06, ZB + H1), (bw + 0.15, 0.14, 0.22), TRIM)
    # фронтон: каменный треугольник + кровля
    gh = bw / 2 * 0.85
    gable(f"GableWall_{tag}", bx - bw / 2, bx + bw / 2, yf, yf + pr + 0.4, ZT, gh, "y", STONE)
    gable(f"GableRoof_{tag}", bx - bw / 2, bx + bw / 2, yf, 4.6, ZT + 0.12, gh, "y", ROOF, over=0.45)
    # лепнина в тимпане
    cyl(f"Medallion_{tag}", (bx, yf - 0.1, ZT + gh * 0.32), 0.45, 0.08, TRIM, 24).rotation_euler = (math.pi / 2, 0, 0)
    ym = (-4.5 - pr + 0.5)

# основная крыша: вальмовая со скатами ко всем сторонам и отдельной кровлей на крыльях
hip("Roof_main", -11, 11, -4.5, 4.5, ZT, 3.6, 5.5, ROOF, over=0.7)
gable("Roof_back_L", -11.5, -4.5, 3.5, 9.5, ZT - 0.6, 3.0, "x", ROOF, over=0.5)
gable("Roof_back_R", 4.5, 11.5, 3.5, 9.5, ZT - 0.6, 3.0, "x", ROOF, over=0.5)

# трубы
chimney("Chimney_1", -10, 1.0, ZT + 1.8, ZT + 5.2)
chimney("Chimney_2", -3.2, 0.8, ZT + 2.3, ZT + 5.6)
chimney("Chimney_3", 3.2, 0.8, ZT + 2.3, ZT + 5.6)
chimney("Chimney_4", 10, 1.0, ZT + 1.8, ZT + 5.2)

# ----------------------------------------------------------- фасад: двери, окна
YW = -4.5                       # стена основного корпуса
YC = -4.5 - 1.6 + 0.5           # передняя плоскость центрального эркера
# крыльцо и дверь
box("Porch_step1", (0, YC - 0.9, 0.2), (3.6, 1.6, 0.4), TRIM)
box("Porch_step2", (0, YC - 0.35, 0.45), (3.0, 1.0, 0.5), TRIM)
for sx in (-1, 1):
    box("Door_pilaster", (sx * 1.2, YC - 0.12, ZB + 1.3), (0.35, 0.25, 2.6), TRIM)
    cyl("Door_lamp", (sx * 1.85, YC - 0.1, ZB + 2.1), 0.1, 0.35, BLACK, 8)
box("Door_leaf", (0, YC - 0.07, ZB + 1.1), (1.5, 0.12, 2.2), DOOR)
cyl("Door_arch", (0, YC - 0.07, ZB + 2.2), 0.75, 0.12, DOOR, 24).rotation_euler = (math.pi / 2, 0, 0)
box("Door_frame_top", (0, YC - 0.12, ZB + 3.05), (3.0, 0.3, 0.2), TRIM)
box("Door_surround", (0, YC - 0.1, ZB + 2.75), (2.4, 0.26, 0.3), TRIM)
for sx in (-1, 1):
    box("Door_panel_line", (sx * 0.38, YC - 0.15, ZB + 1.0), (0.45, 0.04, 1.6), BLACK)
    box("Door_handle", (sx * 0.15, YC - 0.17, ZB + 1.1), (0.05, 0.05, 0.25), IRON)
# окно над дверью + балконный парапет
window(0, YC, ZB + H1 + 1.7, 1.0, 1.7, name="C_up")
box("Door_balcony_ledge", (0, YC - 0.3, ZB + 3.45), (2.0, 0.5, 0.15), TRIM)

# окна центральной части между эркерами
for x in (-4.2, 4.2):
    window(x, YW, ZB + 1.7, 1.0, 1.8, name="Mid_low")
    window(x, YW, ZB + H1 + 1.7, 1.0, 1.7, name="Mid_up")
# окна основного корпуса за боковыми эркерами (внешняя часть)
for x in (-10.4, 10.4):
    window(x, YW, ZB + 1.7, 0.9, 1.8, name="Out_low")
    window(x, YW, ZB + H1 + 1.7, 0.9, 1.7, name="Out_up")

# боковые эркеры: французские окна внизу, балкон наверху
for bx, bw, tag in BAYS[::2]:
    yf = -4.5 - 1.2 + 0.5
    for dx in (-1.3, 1.3):
        window(bx + dx, yf, ZB + 1.55, 1.1, 2.4, name=f"{tag}_french")
        window(bx + dx, yf, ZB + H1 + 1.65, 1.1, 2.3, name=f"{tag}_up_french")
    # балкон над нижним этажом
    box(f"Balcony_floor_{tag}", (bx, yf - 0.5, ZB + H1 - 0.1), (bw + 0.6, 1.1, 0.25), TRIM)
    balustrade(f"Balc_front_{tag}", bx - bw / 2 - 0.25, bx + bw / 2 + 0.25, yf - 1.0, ZB + H1, 1.0)
    balustrade(f"Balc_side_{tag}", yf - 1.0, yf, bx - bw / 2 - 0.25, ZB + H1, 1.0, "y")
    balustrade(f"Balc_side2_{tag}", yf - 1.0, yf, bx + bw / 2 + 0.25, ZB + H1, 1.0, "y")
    for sx in (-1, 1):
        box(f"Balc_column_{tag}", (bx + sx * (bw / 2 - 0.15), yf - 0.15, ZB + H1 / 2), (0.3, 0.2, H1), TRIM)

# тыльная сторона и торцы: ряд окон
for x in (-9, -4, 4, 9):
    window(x, 4.5, ZB + 1.7, 1.0, 1.8, face=1, name="Back_low")
    window(x, 4.5, ZB + H1 + 1.7, 1.0, 1.7, face=1, name="Back_up")
for y in (-2.5, 0, 2.5):
    window(y, -11, ZB + 1.7, 1.0, 1.8, face=1, name="SideL_low", stone_side="x")
    window(y, 11, ZB + 1.7, 1.0, 1.8, face=-1, name="SideR_low", stone_side="x")
    window(y, -11, ZB + H1 + 1.7, 1.0, 1.7, face=1, name="SideL_up", stone_side="x")
    window(y, 11, ZB + H1 + 1.7, 1.0, 1.7, face=-1, name="SideR_up", stone_side="x")

# парапеты (балюстрады) на крыше между эркерами
balustrade("Roof_bal_L", -5.5, -2.7, -4.45, ZT, 0.8)
balustrade("Roof_bal_R", 2.7, 5.5, -4.45, ZT, 0.8)

# плющ
ivy("Ivy_A", -4.3, YW, ZB + 0.5, ZT - 0.3, 1.8)
ivy("Ivy_B", 4.2, YW, ZB + 0.5, ZT - 0.5, 2.2)
ivy("Ivy_C", -6.0, YW - 0.9, ZB + 0.5, ZT, 0.8, n=40)
ivy("Ivy_D", 6.0, YW - 0.9, ZB + 0.5, ZT, 0.8, n=40)
ivy("Ivy_E", -11, 3.0, ZB + 0.5, ZT - 0.5, 4.0, face=1, n=70, side="x")
ivy("Ivy_F", 11, -2.0, ZB + 0.5, ZT - 0.5, 4.0, face=-1, n=70, side="x")

# ----------------------------------------------------------- двор
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, -0.02))
g = bpy.context.object
g.name = "Lawn"
g.scale = (70, 60, 1)
put(g, GRASS)

# круглая площадка с узором
cyl("Court", (0, -17, 0.03), 11.5, 0.06, PAVE, 64)
for i, r in enumerate((10.5, 7.5, 5.0)):
    ring = cyl("Court_ring", (0, -17, 0.07 + i * 0.002), r, 0.04, PAVE2 if i % 2 == 0 else PAVE, 64)
for k in range(24):
    a = k / 24 * math.tau
    box("Court_spoke", (math.cos(a) * 8, -17 + math.sin(a) * 8, 0.1), (5, 0.06, 0.02), PAVE2).rotation_euler = (0, 0, a)
box("Walk_to_house", (0, -7.5, 0.04), (3.4, 6, 0.08), PAVE)
box("Drive_L", (-20, -13, 0.02), (16, 3.2, 0.04), GRAVEL).rotation_euler = (0, 0, -0.2)
box("Drive_R", (20, -13, 0.02), (16, 3.2, 0.04), GRAVEL).rotation_euler = (0, 0, 0.2)

# фонтан в круге живой изгороди
cyl("Fountain_hedge", (0, -17, 0.25), 2.4, 0.5, LEAF, 32)
cyl("Fountain_lawn", (0, -17, 0.52), 2.0, 0.06, GRASS, 32)
cyl("Fountain_base", (0, -17, 0.4), 1.25, 0.35, TRIM, 32)
cyl("Fountain_water", (0, -17, 0.58), 1.1, 0.05, WATER, 32)
cyl("Fountain_stem", (0, -17, 1.0), 0.18, 1.0, TRIM, 16)
cyl("Fountain_bowl", (0, -17, 1.55), 0.6, 0.2, TRIM, 24, 0.25)
cyl("Fountain_top", (0, -17, 1.95), 0.12, 0.6, TRIM, 12)
cyl("Fountain_spray", (0, -17, 2.2), 0.04, 0.5, WATER, 8, 0.15)

# живые изгороди по дуге вокруг площадки
for k in range(24):
    a = math.pi * 0.95 + k / 23 * (math.pi * 1.1) * -1
    a = math.radians(-20 - k * 140 / 23 * 1.0) + math.radians(20)
    ang = math.radians(200 + k * (140 / 23))
    x, y = math.cos(ang) * 13, -17 + math.sin(ang) * 13 * 0.9
    b = box("Hedge_arc", (x, y, 0.55), (2.3, 1.2, 1.1), LEAF)
    b.rotation_euler = (0, 0, ang + math.pi / 2)
box("Hedge_front_L", (-9, -7.3, 0.5), (11, 1.1, 1.0), LEAF)
box("Hedge_front_R", (9, -7.3, 0.5), (11, 1.1, 1.0), LEAF)

# кусты с белыми цветами
for x in (-12.5, -9, -6, 6, 9, 12.5, -3.5, 3.5):
    bush_flowers("Hydrangea", x, -6.4, 16, 1.0)

# кипарисы
for i, x in enumerate((-13.5, -15.5, -17.5, 13.5, 15.5, 17.5, -12.5, 12.5)):
    cypress("Cypress", x, -9.5 + (i % 3) * -3 if abs(x) > 14 else -6.0, 5.5 + (i % 3) * 0.7, 0.8)
for x, y in ((-21, -17), (21, -17), (-20, -3), (20, -3), (-14, 8), (14, 8)):
    cypress("Cypress_far", x, y, 7, 1.0)

# столбики у входа на площадку
for x in (-5.2, 5.2):
    box("Gatepost", (x, -7.6, 0.6), (0.45, 0.45, 1.2), TRIM)
    box("Gatepost_cap", (x, -7.6, 1.28), (0.6, 0.6, 0.12), TRIM)

# ----------------------------------------------------------- оранжерея и бассейн (справа)
GX, GY = 17.5, 5.5
box("Greenhouse_base", (GX, GY, 0.3), (8, 7, 0.6), TRIM)
box("Greenhouse_glass", (GX, GY, 2.4), (7.8, 6.8, 3.6), GLASS)
for i in range(9):
    x = GX - 3.9 + i * 0.975
    box("Greenhouse_mullion", (x, GY - 3.4, 2.4), (0.06, 0.06, 3.6), TRIM)
    box("Greenhouse_mullion", (x, GY + 3.4, 2.4), (0.06, 0.06, 3.6), TRIM)
for i in range(8):
    y = GY - 3.4 + i * 0.97
    box("Greenhouse_mullion_s", (GX - 3.9, y, 2.4), (0.06, 0.06, 3.6), TRIM)
    box("Greenhouse_mullion_s", (GX + 3.9, y, 2.4), (0.06, 0.06, 3.6), TRIM)
box("Greenhouse_rail_low", (GX, GY - 3.42, 1.2), (7.9, 0.07, 0.07), TRIM)
box("Greenhouse_rail_up", (GX, GY - 3.42, 3.0), (7.9, 0.07, 0.07), TRIM)
gable("Greenhouse_roof", GX - 4.0, GX + 4.0, GY - 3.5, GY + 3.5, 4.2, 1.8, "x", GLASS, over=0.15)
box("Greenhouse_ridge", (GX, GY, 6.0), (8.2, 0.12, 0.12), TRIM)

# терраса с шахматной плиткой и бассейн
for i in range(12):
    for j in range(8):
        box("Terrace_tile", (GX - 5.5 + i * 1.0 - 0.0 + 0.5 - 3.0 + 0.5, -4.5 + j * 1.0, 0.05), (1.0, 1.0, 0.1),
            BLACK if (i + j) % 2 else TRIM)
box("Pool_edge", (GX + 1.0, -2.0, 0.1), (7.4, 4.8, 0.2), TRIM)
box("Pool_water", (GX + 1.0, -2.0, 0.15), (6.6, 4.0, 0.12), WATER)
for sx in (-1, 1):
    box("Pool_step", (GX + 1.0 + sx * 3.7, -2.0, 0.06), (0.5, 1.2, 0.08), TRIM)
# зонты и шезлонги
for x, y in ((GX - 3, -4.5), (GX - 3, 0.0)):
    cyl("Umbrella_pole", (x, y, 1.1), 0.04, 2.2, TRIM, 8)
    cyl("Umbrella", (x, y, 2.3), 1.1, 0.35, TRIM, 16, 0.05)
for k in range(3):
    box("Lounger", (GX - 5.2, -4.0 + k * 1.3, 0.35), (0.7, 1.8, 0.15), TRIM)
    box("Lounger_back", (GX - 5.2, -3.1 + k * 1.3, 0.55), (0.7, 0.1, 0.5), TRIM).rotation_euler = (-0.5, 0, 0)

# ----------------------------------------------------------- свет, камера, рендер
bpy.ops.object.light_add(type="SUN", location=(20, -30, 40))
sun = bpy.context.object
sun.data.energy = 4
sun.rotation_euler = (math.radians(50), 0, math.radians(35))
w = bpy.data.worlds.new("W")
w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.85, 0.95, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
bpy.context.scene.world = w

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "house.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "house.glb"), export_format="GLB")
try:
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "house.fbx"), path_mode="COPY", embed_textures=False)
except Exception as e:
    print("fbx skipped", e)

sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.device = "CPU"
sc.render.resolution_x, sc.render.resolution_y = 1280, 800
cam_d = bpy.data.cameras.new("Cam")
cam_d.lens = 28
cam = bpy.data.objects.new("Cam", cam_d)
sc.collection.objects.link(cam)
sc.camera = cam
for name, loc, tgt in (("front", (-6, -48, 22), (2, -5, 4)), ("side", (45, -30, 20), (8, -2, 3))):
    cam.location = loc
    d = (bpy.mathutils.Vector(tgt) if hasattr(bpy, "mathutils") else __import__("mathutils").Vector(tgt)) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.render.filepath = os.path.join(OUT, f"preview_{name}.png")
    bpy.ops.render.render(write_still=True)
print("OK objects:", len(col.objects))
