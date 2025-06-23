#!/usr/bin/env python3

from os import path, rename, listdir
from PIL import Image

# TODO: Not working correctly. resizing both new and original file
size = 96, 96

script_root = path.dirname(path.realpath(__file__))

file_list = [file for file in listdir(script_root) if file.lower().endswith(".png")]

for file in file_list:
    newfile = list(path.splitext(file))
    newfile.insert(1, "_orig")
    newfile = "".join(newfile)
    rename(
        file,
        newfile,
    )
    try:
        im = Image.open(newfile)
        im.thumbnail(size, Image.Resampling.LANCZOS)
        im.save(file)
    except Exception as e:
        print(f"{type(e).__name__}: e")
print(file_list)
