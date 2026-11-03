def lum(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16)/255 for i in (0, 2, 4)]
    c = [x/12.92 if x <= 0.04045 else ((x+0.055)/1.055)**2.4 for x in c]
    return 0.2126*c[0] + 0.7152*c[1] + 0.0722*c[2]


def r(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi+0.05)/(lo+0.05), 2)


# brand gradient ends
for hexv in ["#2c6bed", "#7c3aed"]:
    print(f"white on {hexv}: {r('#ffffff', hexv)}")
# scrim over a mid-grey media placeholder
print("white over scrim-on-#e6ecf3:", r("#ffffff", "#3f454d"))
print("white over scrim-on-#000000:", r("#ffffff", "#000000"))
