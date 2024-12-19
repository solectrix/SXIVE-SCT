import pandas as pd
import os
import re
import sys
sys.path.append("../..")
from sxl import Sxl, SxlRoot

sensor_id = "IMX623"
xlsx_file = "IMX623-AAQV_RegisterMap_E_Rev1.0.1.xlsx"
device_addr = 0x00

# replacement map of description text, selection of problematic characters
char_map = {"\u2019": "'",
            "≤": "<=", 
            "\u2264": "<=",
            "\u2013": "-",
            "\u2022": "*", 
            "\u03bc": "u",
            "μ": "u",
            "\uff64": ",",
            "\"": "'"}

# open file
try:
    ef = pd.ExcelFile(xlsx_file)
except Exception as e:
    print("Error:", e)
    exit()

# keyword identifiers
class ID:
    cat         = "Category"
    cat_no      = "Category No"
    cat_name    = "Category Name"
    sig_name    = "Register Name"
    addr_offset = "Offset"
    addr_i2c    = "I2C Address"
    sig_desc    = "Description"
    sig_unit    = "Unit"
    sig_mode    = "R/W"
    sig_pos     = "BIT"
    sig_reset   = "Default Value"
    sig_bytes   = "Register Unit(Byte)"

print(f"Reading register definitions file '{xlsx_file}'")

cat = ef.parse(ID.cat, header=1)
if ID.cat_no not in cat.columns or \
   ID.cat_name not in cat.columns:
    print("Error: Unexpected sheet content!")
    exit()

# prepare SXL
sxl_root = SxlRoot()

sxl_icon = sxl_root.new(Sxl.Icon, sensor_id)
sxl_icon.new(Sxl.Mst, sensor_id, {"desc": f"top of {sensor_id} for address space compilation"})

sxl_icon_top = sxl_root.new(Sxl.Icon, "top")
sxl_icon_top.new(Sxl.Mst, "top", {"desc": "top level of address space"})
sxl_icon_top.new(Sxl.Slv, sensor_id, {"icon": sensor_id, "addr": f"0x{device_addr:02X}000000", "size": "0x00010000"})

no_reserved = 0
blocks_addr = dict()
blocks_size = dict()

# iterate over 
for i in range(cat.shape[0]):
    cat_id = cat.at[i, ID.cat_no]
    cat_name = cat.at[i, ID.cat_name]
    print(f"  Parsing block: {cat_name}")
    
    # extract block
    block = ef.parse(cat_name, header=1)
    block_shape = block.shape

    # sanity check
    ok = True
    for item in [ID.sig_name, ID.addr_offset, ID.addr_i2c, ID.sig_desc, ID.sig_unit,
                 ID.sig_mode, ID.sig_pos, ID.sig_reset, ID.sig_bytes]:
        if item not in block.columns:
            ok = False
            break
    if not ok:
        print(f"Error: Category '{cat_name}' invalid!")
        continue

    # create SXL block
    sxl_block = sxl_root.new(Sxl.Block, cat_name)
    if cat_id != "-":
        sxl_block.set_attr("tags", f"Category:{cat_id}")

    # cycle through all existing signals
    sig_offset = None
    block_addr = 0
    block_size = 0

    for idx in range(block_shape[0]):
        sig_name    = block.at[idx, ID.sig_name]
        addr_offset = block.at[idx, ID.addr_offset]
        addr_i2c    = block.at[idx, ID.addr_i2c]
        sig_desc    = block.at[idx, ID.sig_desc]
        sig_unit    = block.at[idx, ID.sig_unit]
        sig_mode    = block.at[idx, ID.sig_mode]
        sig_pos     = block.at[idx, ID.sig_pos]
        sig_reset   = block.at[idx, ID.sig_reset]
        sig_bytes   = block.at[idx, ID.sig_bytes]

        # update addr offset if possible        
        if isinstance(addr_offset, str):
            sig_offset = addr_offset
            if isinstance(addr_i2c, str):
                val_list = block.at[idx, ID.addr_i2c].split(",")
                sig_addr = val_list[0]

                if cat_id != "-":
                    if block_size == 0:
                        # addresses are given in 16bit hex, convert to integer
                        block_addr = int(sig_addr, 16) - int(addr_offset, 16)
                        block_size = int(sig_addr, 16) - int(addr_offset, 16) + int(sig_bytes)
                    else:
                        # update size?
                        block_size = int(addr_offset, 16) + int(sig_bytes)
                else:
                    block_size = 0x10000
                    sig_offset = sig_addr

        # ignore all "RESERVED" signals
        if sig_name == "RESERVED":
            no_reserved += 1
            continue
        
        # create SXl Signal
        sxl_signal = sxl_block.new(Sxl.Sig, sig_name, dict(addr=sig_offset, pos=sig_pos))

        if isinstance(addr_offset, str):
            if sig_desc != "":
                sig_desc = re.compile("|".join(char_map.keys())).sub(lambda ele: char_map[re.escape(ele.group(0))], sig_desc)
                # add SXL desc attribute to signal
                sxl_signal.set_attr("desc", sig_desc)

        if isinstance(sig_reset, str) and sig_reset != "-":
            # in the present version of the register definition,
            # there are false hex reset values, we interpret them as hex
            match = re.findall(r"^(0B[0-9A-F]+)$", sig_reset)
            if len(match) == 1:
                sig_reset = f"0x{int(match[0], 16):X}" 
            # add SXL reset attribute to signal
            sxl_signal.set_attr("reset", sig_reset)

        # signal access mode, "rw" by default if not set differently
        if sig_mode == "R":
            sxl_signal.set_attr("mode", "ro")
        elif sig_mode == "W":
            sxl_signal.set_attr("mode", "wo")

        # extract potential enums
        enums_found = False
        if isinstance(sig_desc, str):
            for line in sig_desc.split("\n"):
                match = re.findall(r"^([0x]*[0-9a-fA-F]+): (.*)", line)
                if len(match) == 1:
                    enums_found = True
                    enum, enumdesc = match[0]
                    enum = str(int(enum, 0))
                    sxl_signal.new(Sxl.Enum, f"E{enum}", dict(value=enum, desc=enumdesc))
            
            if enums_found:
                # add SXL type attribute to signal
                sxl_signal.set_attr("type", "enum")

        # extract fixed point notation
        if isinstance(sig_unit, str) and not enums_found:
            if sig_unit[0].lower() == "s":
                fixpoint = sig_unit[1:].split(".")
                if len(fixpoint) == 2:
                    fpInt, fpFrac = fixpoint
                    # correct signed fixpoint notation
                    sig_unit = f"S{int(fpInt)+1}.{fpFrac}"

            # add SXL type attribute
            sxl_signal.set_attr("type", sig_unit)

        if cat_id == "-" and ID.cat_no in block.columns:
            cat_no = block.at[idx, ID.cat_no]
            sxl_signal.set_attr("tags", f"Category:{cat_no}")


    # create SXL slave binding
    sxl_slv = sxl_icon.new(Sxl.Slv, cat_name, {Sxl.Block: cat_name})
    sxl_slv.set_attr("addr", f"0x{block_addr:04X}")
    sxl_slv.set_attr("size", f"0x{block_size:04X}")

ef.close()
print(f"Info: A number of {no_reserved} reserved signals were ignored.")

# create SXL file
sxl_path = os.path.splitext(xlsx_file)[0] + ".sxl"
sxl_root.save(sxl_path)
print(f"SXL file '{sxl_path}' generated.")
