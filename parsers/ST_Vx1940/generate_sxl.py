import os
from xml.dom.minidom import parse

import sys
sys.path.append("../..")
from sxl import Sxl, SxlRoot

sensor_id = "Vx1940"
xml_file  = "Vx1940_UI_03.01.xml"
device_addr = 0x00

debug = False

print(f"Reading register definitions file '{xml_file}'")

# get document DOM tree
document = parse(xml_file)

# cycle trough DOM elements
elem = document.documentElement
    
# check prefix
if elem.prefix != "spirit":
    print("Unexpected document type!")
    exit()

# prepare SXL
sxl_root = SxlRoot()

sxl_icon = sxl_root.new(Sxl.Icon, sensor_id)
sxl_icon.new(Sxl.Mst, sensor_id, {"desc": f"top of {sensor_id} for address space compilation"})

sxl_icon_top = sxl_root.new(Sxl.Icon, "top")
sxl_icon_top.new(Sxl.Mst, "top", {"desc": "top level of address space"})
sxl_icon_top.new(Sxl.Slv, sensor_id, {"icon": sensor_id, "addr": f"0x{device_addr:02X}000000", "size": "0x00010000"})

# parse input file structure
for item in elem.childNodes:
    if item.localName in ("vendor", "library", "name", "version"):
        if debug: print(f"{item.localName}: {item.childNodes[0].data}")

    elif item.localName == "busInterfaces":
        for ifcs in item.childNodes:
            if ifcs.localName == "busInterface":
                for ifc in ifcs.childNodes:
                    if ifc.localName is not None and ifc.localName in ("name"):
                        if debug: print("\nBusInterface:", ifc.childNodes[0].data)
                    elif ifc.localName == "parameters":
                        for pars in ifc.childNodes:
                            name_, value_ = None, None
                            if pars.localName == "parameter":
                                for par in pars.childNodes:
                                    if par.localName == "name":
                                        name_ = par.childNodes[0].data
                                    elif par.localName == "value":
                                        value_ = par.childNodes[0].data
                            if name_ and value_:
                                if debug: print(f"  {name_}: {value_}")

    elif item.localName == "memoryMaps":
        for maps in item.childNodes:
            if maps.localName == "memoryMap":
                for map in maps.childNodes:
                    if map.localName and map.localName in ("name"):
                        if debug: print(f"\nMemoryMap: {map.childNodes[0].data}")
                    elif map.localName == "addressBlock":
                        # cycle through all address blocks
                        for ablk in map.childNodes:
                            if ablk.localName == "name":
                                print(f"  Parsing block: {ablk.childNodes[0].data}")
                                block_name = ablk.childNodes[0].data
                                sxl_block = sxl_root.new(Sxl.Block, ablk.childNodes[0].data)
                                sxl_slv = sxl_icon.new(Sxl.Slv, ablk.childNodes[0].data, {"block": ablk.childNodes[0].data})
                            elif ablk.localName == "baseAddress":
                                sxl_slv.set_attr("addr", ablk.childNodes[0].data)
                            elif ablk.localName == "range":
                                sxl_slv.set_attr("size", ablk.childNodes[0].data)
                            elif ablk.localName == "width":
                                pass
                            elif ablk.localName == "register":
                                # cycle through all registers
                                regReset = 0
                                for reg in ablk.childNodes:
                                    if reg.localName == "name":
                                        regName = reg.childNodes[0].data
                                        sxl_reg = sxl_block.new(Sxl.Reg, reg.childNodes[0].data)
                                    elif reg.localName == "description":
                                        sxl_reg.set_attr("desc", reg.childNodes[0].data)
                                    elif reg.localName == "addressOffset":
                                        sxl_reg.set_attr("addr", f"0x{int(reg.childNodes[0].data, 0):04X}")
                                    elif reg.localName  == "size":
                                        size = int(reg.childNodes[0].data)
                                        if size == 8:
                                            sxl_reg.set_attr("type", "byte")
                                        elif size == 16:
                                            sxl_reg.set_attr("type", "word")
                                        elif size != 32:
                                            raise ValueError(f"Bad register size: {size}!")
                                    elif reg.localName == "typeIdentifier":
                                        sxl_reg.set_attr("tags", reg.childNodes[0].data)
                                    elif reg.localName in ("displayName", "access"):
                                        pass
                                    elif reg.localName == "dim":
                                        pass
                                    elif reg.localName == "reset":
                                        # cycle through all reset values
                                        for reset in reg.childNodes:
                                            if reset.localName and reset.localName in ("value"):
                                                regReset = int(reset.childNodes[0].data, 0)
                                    
                                    elif reg.localName == "field":
                                        # cycle through all fields (signals) attributes
                                        sig_pos = None
                                        sigWidth = None
                                        for field in reg.childNodes:
                                            if field.localName is not None and field.localName in ("name",):
                                                sxl_sig = sxl_reg.new(Sxl.Sig, field.childNodes[0].data)
                                            elif field.localName is not None and field.localName in ("description"):
                                                sxl_sig.set_attr("desc", field.childNodes[0].data)
                                            elif field.localName is not None and field.localName in ("bitOffset",):
                                                sig_pos = int(field.childNodes[0].data)
                                            elif field.localName is not None and field.localName in ("bitWidth",):
                                                sigWidth = int(field.childNodes[0].data)
                                                if sig_pos is not None and sigWidth is not None:
                                                    if sigWidth == 1:
                                                        sxl_sig.set_attr("pos", f"{sig_pos}")
                                                    else:
                                                        sxl_sig.set_attr("pos", f"{sigWidth+sig_pos-1}:{sig_pos}")
                                            elif field.localName == "access":
                                                mode = field.childNodes[0].data
                                                if mode == "read-write" or mode == "read-only":
                                                    sxl_sig.set_attr("mode", "ro" if mode == "read-only" else "rw")
                                                else:
                                                    raise ValueError(f"Bad signal mode {mode}")
                                                    
                                            elif field.localName == "enumeratedValues":
                                                #continue
                                                # cycle through enums
                                                for enums in field.childNodes:
                                                    if enums.localName == "enumeratedValue":
                                                        for enum in enums.childNodes:
                                                            if enum.localName == "name":
                                                                sxl_sig.set_attr("type", "enum")
                                                                sxl_enum = sxl_sig.new(Sxl.Enum, enum.childNodes[0].data)
                                                            elif enum.localName == "description":
                                                                sxl_enum.set_attr("desc", enum.childNodes[0].data.strip())
                                                            elif enum.localName == "value":
                                                                sxl_enum.set_attr("value", int(enum.childNodes[0].data, 0))
                                                            elif enum.localName:
                                                                print(f"UNSUPPORTED ENUM ATTRIBUTE: {enum.localName}")
                                                
                                            elif field.localName:
                                                print(f"UNSUPPORTED FIELD ATTRIBUTE: {field.localName}")
                                        # finally set reset value
                                        if sig_pos is not None and sigWidth is not None:
                                            sig_reset = (regReset >> sig_pos) & ((1 << sigWidth)-1)
                                            sxl_sig.set_attr("reset", f"0x{sig_reset:04X}")
                                        
                                    elif reg.localName:
                                        print(f"UNSUPPORTED REGISTER ATTRIBUTE: {reg.localName}")
                            elif ablk.localName == "parameters":
                                # ignore parameters
                                pass
                            elif ablk.localName:
                                print(f"UNSUPPORTED ADDRESSBLOCK ATTRIBUTE: {ablk.localName}")
                    elif map.localName:
                        print(f"UNSUPPORTED ADDRESSMAP ATTRIBUTE: {map.localName}")

    elif item.localName == "parameters":
        if debug: print("\nParameters:")
        for pars in item.childNodes:
            name_, value_ = None, None
            if pars.localName == "parameter":
                for par in pars.childNodes:
                    if par.localName == "name":
                        name_ = par.childNodes[0].data
                    elif par.localName == "value":
                        value_ = par.childNodes[0].data
            if name_ and value_:
                if debug: print(f"  {name_}: {value_}")

    elif item.localName:
        if debug: print(f"UNSUPPORTED COMPONENT ATTRIBUTE: {item.localName}")

# create SXL file
sxl_path = os.path.splitext(xml_file)[0] + ".sxl"
sxl_root.save(sxl_path)
print(f"\nSXL file '{sxl_path}' generated.")
