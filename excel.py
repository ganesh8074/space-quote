# interior_estimator.py

# ---------- master data ----------
plywood = [
    ("Century club prime BWP 710", 138),
    ("Club prime commercial MR", 122),
    ("Green gold 710 BWP", 136),
    ("Green gold commercial", 123),
    ("Maxi platinum", 95),
    ("Red Daimond", 106),
    ("Century Sainik", 86),
    ("Green Ecotec", 86),
    ("Orchid", 68),
]

hinges = [
    ("Ebco zero crank normal", 60),
    ("Ebco eight crank normal", 62),
    ("Ebco zero crank soft", 120),
    ("Ebco eight crank soft", 125),
    ("Hitteck zero crank normal", 83),
    ("Hitteck eight crank normal", 86),
    ("Hitteck zero crank soft", 140),
    ("Hitteck eight crank soft", 150),
]

channels = [
    ("EBCO 20 inch normal", 360),
    ("EBCO 20 inch soft", 670),
    ("EBCO 18 inch normal", 330),
    ("EBCO 18 inch soft", 625),
    ("EBCO 16 inch normal", 300),
    ("EBCO 16 inch soft", 600),
    ("EBCO 14 inch normal", 295),
    ("EBCO 14 inch soft", 575),
    ("EBCO 12 inch normal", 255),
    ("EBCO 12 inch soft", 475),
    ("EBCO 10 inch normal", 185),
    ("Hittecfh 20 inch normal", 390),
    ("Hittecfh 20 inch soft", 1020),
    ("Hittecfh 18 inch normal", 380),
    ("Hittecfh 18 inch soft", 990),
    ("Hittecfh 16 inch normal", 370),
    ("Hittecfh 16 inch soft", 970),
    ("Hittecfh 14 inch normal", 350),
    ("Hittecfh 14 inch soft", 960),
    ("Hittecfh 12 inch normal", 345),
    ("Hittecfh 12 inch soft", 950),
]

sliding_tracks = [
    ("CNR 8 feet 2 door", 3800),
    ("EBCO 8 feet 2 door", 4750),
    ("Hettic 8 feet 2 door", 3850),
    ("Haffle 8 feet 2 door", 5100),
]

doors = [
    ("Normal company door (per sqft)", 850),
    ("Aristo company door (per sqft)", 2300),
    ("Profile door (per sqft)", 600),
]

# (name, min_per_sqft, max_per_sqft)
laminates = [
    ("Inner 0.8mm (per sqft)", 370, 370),
    ("Inner 1mm (per sqft)", 550, 600),
    ("Outer Century M 1mm (per sqft)", 1600, 1600),
    ("Outer Century high glossy (per sqft)", 2550, 2550),
    ("Outer Royal Touch matt (per sqft)", 2200, 2200),
    ("Outer Royal Touch glossy (per sqft)", 3500, 3500),
    ("Outer Acrylic (per sqft)", 2600, 4000),
]

# (name, min, max)
handles = [
    ("8 inch", 100, 500),
    ("2 feet", 800, 1500),
    ("4 feet", 1000, 2000),
]


def choose_from_list(title, data, has_range=False):
    print(f"\n--- {title} ---")
    for i, item in enumerate(data, start=1):
        if has_range:
            print(f"{i}. {item[0]}  -> {item[1]} to {item[2]}")
        else:
            print(f"{i}. {item[0]}  -> {item[1]}")
    while True:
        try:
            choice = int(input("Select option number: "))
            if 1 <= choice <= len(data):
                return data[choice - 1]
        except ValueError:
            pass
        print("Invalid choice, try again.")


def main():
    print("INTERIOR ESTIMATOR (console)")
    # area is for door + laminate
    area = float(input("Enter area in sqft (for doors/laminates): "))

    ply = choose_from_list("Plywood", plywood)
    hinge = choose_from_list("Hinge", hinges)
    channel = choose_from_list("Channel", channels)
    sliding = choose_from_list("Sliding Track", sliding_tracks)
    door = choose_from_list("Door/Profile (per sqft)", doors)
    laminate = choose_from_list("Laminate (per sqft)", laminates, has_range=True)
    handle = choose_from_list("Handle", handles, has_range=True)

    # fixed parts
    fixed_total = ply[1] + hinge[1] + channel[1] + sliding[1]

    # door is per sqft
    door_total = door[1] * area

    # laminate range
    lam_min = laminate[1] * area
    lam_max = laminate[2] * area

    # handle range
    han_min = handle[1]
    han_max = handle[2]

    total_min = fixed_total + door_total + lam_min + han_min
    total_max = fixed_total + door_total + lam_max + han_max

    print("\n========== BILL ==========")
    print(f"Plywood: {ply[0]} = {ply[1]}")
    print(f"Hinge: {hinge[0]} = {hinge[1]}")
    print(f"Channel: {channel[0]} = {channel[1]}")
    print(f"Sliding Track: {sliding[0]} = {sliding[1]}")
    print(f"Door: {door[0]} @ {door[1]} per sqft × {area} = {door_total}")
    print(f"Laminate: {laminate[0]} -> {laminate[1]} to {laminate[2]} per sqft × {area} = {lam_min} to {lam_max}")
    print(f"Handle: {handle[0]} -> {handle[1]} to {handle[2]}")
    print("---------------------------")
    print(f"TOTAL (min): {total_min}")
    print(f"TOTAL (max): {total_max}")
    print("========== END ==========")


if __name__ == "__main__":
    main()
