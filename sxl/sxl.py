"""Simplified SXL library."""

import os
import tkinter
import warnings
from copy import copy

warnings.simplefilter("default")

SPACE = " "
NEWLINE = "\n"

# SXL identifiers
class Sxl:
    Root = "root"
    Dev = "device"
    Block = "block"
    Reg = "register"
    Sig = "signal"
    Enum = "enum"
    Flag = "flag"
    Icon = "intercon"
    Mst = "master"
    Slv = "slave"

# load the sxl config
class SxlConfig:
    """SXL Config class."""
    def __init__(self, sxl_dict: dict = None):
        if not sxl_dict is None:
            for key in sxl_dict.keys():
                if isinstance(sxl_dict[key], dict):
                    setattr(self, key, SxlConfig())
                    for sub_key in sxl_dict[key]:
                        if isinstance(sxl_dict[key][sub_key], (list, str)):
                            # get the sub_dict
                            sub_dict = getattr(self, key)
                            # set the value for sub_dict
                            setattr(sub_dict, sub_key, sxl_dict[key][sub_key])
                            # assign back the sub_dict
                            setattr(self, key, sub_dict)
                        else:
                            raise ValueError(
                                f"SXL Config: Structure not supported: key '{key}', sub_key '{sub_key}', type '{type(sxl_dict[key][sub_key])}'"
                            )
                elif isinstance(sxl_dict[key], str):
                    setattr(self, key, sxl_dict[key])
                else:
                    raise ValueError(
                        f"SXL Config: Structure not supported: key '{key}, type '{type(sxl_dict[key])}'!"
                    )


class SxlObject:
    """SXL general object class
    * :attr:`parent` private parent of the object being created
    * :attr:`name` private name of the object, can be set by creating the object and
        read by function getName()
    * :attr:`attr_dict` private list of assigned child objects
        objects can be:
        - added by function 'add_object()' and
        - retrieved by various functions, like: getObjects(), get_object_of_name(), getObjectOfType(), ...
        Objects attributes can also be determined by function num_objects()
    """

    def __init__(self, parent, name: str, attr_dict: dict):
        self.config = SxlConfig(DEFAULT_SXL_CONFIG)
        self._parent = parent
        self._name = name
        obj_dict = getattr(self.config, attr_dict)
        self._type = obj_dict.type
        self._objs = list()
        self._attrs = dict()
        self._attr_list = obj_dict.attrs

    @property
    def parent(self):
        """Returns the parent of the object."""
        return self._parent

    @property
    def name(self):
        """Returns the name of the object."""
        return self._name

    @property
    def type(self):
        """Returns the type of the object."""
        return self._type

    @property
    def objects(self):
        """Returns a list of all registered objects."""
        return self._objs

    @property
    def attrs(self):
        """Returns the attributes of the object."""
        return self._attrs

    @property
    def attr_list(self):
        """Returns the available attribute list of the object."""
        return self._attr_list

    def init(self):
        """Initialize object list."""
        # cleanup
        for obj in self._objs:
            obj.init()
            del obj
        # renew object list
        self._objs = list()

    def set_attr(self, attr_name, attr_value):
        """Set an SxlObject's attribute value.
        Args:
            attr_name - identifier of the SxlObject's attribute
            attr_value - value of the SxlObject's attribute"""
        if attr_name not in self._attr_list:
            raise NameError(attr_name)
        else:
            self._attrs[attr_name] = attr_value

    def get_attr(self, attr_name, default=""):
        """Get the SxlObject's attribute value
        Args:
            attr_name - identifier (name) of the SxlObject's attribute,
                       returns default string if not existing"""
        if attr_name not in self._attr_list:
            raise NameError(attr_name)
        elif attr_name not in self._attrs.keys():
            return default
        else:
            return self._attrs[attr_name]

    def has_attr(self, attr_name):
        """Check availability of SxlObject's attribute.
        Args:
            attr_name - identifier (name) of the SxlObject's attribute,
                       returns bool of existence
        """
        return attr_name in self._attr_list and attr_name is not None

    def num_objects(self):
        """Returns the number of registered child objects of a parent object."""
        return len(self._objs)

    def num_objects_of_type(self, type) -> int:
        """Returns the number of registered types."""
        return len([i for i in self._objs if i.type == type])

    def get_object_type_list(self, type):
        """Return a list of object types."""
        return [i for i in self._objs if i.type == type]

    def get_objects_of_type(self, type):
        """Function to return a child object list with an explicit type.
        Args:
            type - instance type to compile for
        """
        objs = list()
        for obj in self._objs:
            if obj.type == type:
                # check current level
                objs.append(obj)
            else:
                # check sub-levels when relevant
                objs.extend(obj.get_objects_of_type(type))
        return objs

    def get_object_of_name(self, name):
        """Function to return a child object with an explicit name identifier.
        Args:
            name - name identifier to look for
        """
        obj = [i for i in self._objs if i.name == name]
        if not obj:
            return None
        else:
            return obj[0]

    def add_object(self, obj):
        """Function to add a child object to a SXL object parent.
        Args:
            obj - object of type SxlObject to be added
        """
        # check for object duplicates
        if obj in self._objs:
            raise ValueError("Object already added!")
        # check for name and type duplicates
        o_name = obj.name
        o_type = obj.type
        for o in self._objs:
            if o_name == o.name and o_type == o.type:
                msg = (
                    f"An object of type '{o_type}' and name '{o_name}' already exists!"
                )
                raise ValueError(msg)
        # all great
        self._objs.append(obj)
        return obj

    def new(self, type: type, name: str, attr_dict: dict = {}):
        """function to create a new SXL object.
        Args:
            type: type of the new object
            name; name of the new object
            parsDict: a dict of SXL 'parameter' attributes of the new object
        .. note::
            the plausibility check is temporary
        """
        # validate consistency of definition (check with hierarchy configuration) and
        # retrieve type specifier
        child_type = self._get_child_type(self, type)
        # create the new object
        obj = self.add_object(obj=SxlObject(self, name, child_type))
        for i in attr_dict.keys():
            obj.set_attr(attr_name=i, attr_value=attr_dict[i])
        return obj

    def copy(self, new_parent=None):
        """Create a copy of object, modify parent if required."""
        new_obj = copy(self)
        if new_parent:
            new_obj._parent = new_parent
        return new_obj

    ##################### Helper functions #####################
    def _get_child_type(self, obj, child_type):
        """Check plausibility of requested object type and return a proper.
        SXL Type classifier.
        An exception is thrown when an unexpected type was requested.
        Args:
            type: type of the new object
        """
        for child in getattr(self.config.hierarchy, obj.type):
            if getattr(self.config, child).type == child_type:
                return child  # found
        raise ValueError(
            f'hierarchy error with "{obj.name}:{obj.type}", no child type "{child_type}" possible!'
        )

    ##################### Debug Output #####################
    def print_debug(self):
        """Debug output: show full SXL structure"""
        print(f"{self._name} ({self._type})")
        for i in self._attrs.keys():
            print(f"  :{i:5}: {self._attrs[i]}")
        for i in self._objs:
            i.print_debug()


class SxlRoot(SxlObject):
    """SXL root object class.
    * :attr:`_objs` private list of assigned child objects
        objects can be:
        - added by function 'add_object()' and
        - retrieved by various functions, like: getObjects(), get_object_of_name(), getObjectOfType(), ...
        Objects attributes can also be determined by function num_objects()
    Args:
        name: identifier of the object, can be in CamelCase format
        attr_dict: descriptor of the object type according to SXL Config applied
    """

    def __init__(self):
        super().__init__(parent=None, name=Sxl.Root, attr_dict="root_type")
        self.groups = True  # do create item groups, or not
        self.tcl = tkinter.Tcl()

    def _strip_dict(self, data_dict):
        """Split string into dict in fashion: {'name1': 'string1', 'name2': 'string2'}.
        NOTE: this feature makes use of the TCL feature 'tkinter._splitdict' to mask TCL groups separated by {} into one string plus
            it removed non-printable characters around them, it keeps all other subgroups together
        """
        try:
            result = tkinter._splitdict(self.tcl, data_dict.strip())
        except:
            return {}
        return result

    def init(self):
        """Call init from parent class. Deletes any objects."""
        super().init()

    ##################### SXL Import #####################
    def import_object_tree(self, root):
        """Import object tree from another root object."""
        if root.type != "root":
            raise ValueError("Object is not a root object!")
        for obj in root.objects:
            if obj in self.objects:
                raise ValueError("Object already exists!")
            else:
                # create copy of existing object, replace objects root parent with new root object
                new = obj.copy(self)
                # add object to own root object
                self.add_object(new)

    ##################### SXL Loader #####################
    def load(self, file, verbose=False):
        """Parse file for registered SXL structure."""

        def parse_level(parent, level, data_dict, verbose=False):
            if level == self.config.Dev:
                # root attributes == device attributes
                sxl_type = level
                sxl_types = [self.config.Dev]
                sxl_attrs = self.config.root_type.attrs
                for item_attr in data_dict.keys():
                    if item_attr in sxl_attrs:
                        if verbose:
                            print("    Attr:", item_attr, "=", data_dict[item_attr])
                        # Add item's attribute to SXL root: name=item_attr, data=data_dict[item_attr], parent=obj
                        parent.set_attr(item_attr, data_dict[item_attr])
            else:
                # all other SXL types
                sxl_type = level[:-1]
                sxl_types = [
                    getattr(self.config, i).type
                    for i in getattr(self.config.hierarchy, parent.type)
                ]
                sxl_attrs = [
                    getattr(self.config, i).attrs
                    for i in getattr(self.config.hierarchy, parent.type)
                ]

                if sxl_type in sxl_types:
                    if verbose:
                        print("Group:", sxl_type)
                    # permitted attributes of a type
                    sxl_type_attrs = sxl_attrs[sxl_types.index(sxl_type)]
                    for item_name in data_dict.keys():
                        if verbose:
                            print("  Name:", item_name)
                        # Create SXL object: name=item_name, type=sxl_type, parent=???
                        obj = parent.new(sxl_type, item_name)
                        # cycle through all potential attributes of the item
                        level_items = self._strip_dict(data_dict[item_name])
                        for item_attr in level_items.keys():
                            if item_attr in sxl_type_attrs:
                                if verbose:
                                    print(
                                        "    Attr:",
                                        item_attr,
                                        "=",
                                        level_items[item_attr],
                                    )
                                # Add item's attribute to SXL object: name=item_attr, data=level_items[item_attr], parent=obj
                                obj.set_attr(item_attr, level_items[item_attr])
                            else:
                                # unknown attribute name, try to parse further SXL levels
                                parse_level(
                                    obj,
                                    item_attr,
                                    self._strip_dict(level_items[item_attr]),
                                    verbose,
                                )
                else:
                    print(
                        f"Undefined attribute '{level}' (name:{parent.name}, type:{parent.type}) ignored."
                    )

        # open file and read content to load_data
        with open(file, "r") as fid:
            load_data = fid.read()
        # split data into dict
        data_dict = self._strip_dict(load_data)
        if len(data_dict) == 0:
            return "File is empty or corrupted!"
        # cycle through all top groups
        for item_type in data_dict.keys():
            parse_level(
                self, item_type, self._strip_dict(data_dict[item_type]), verbose
            )
        return None

    ##################### SXL Saver #####################
    def save(self, file):
        """Save full SXL structure to file.
        Args:
            file - filename
        """

        def add_attrs(f, obj, indent):
            """Write attributes to file.
            Args:
                f - file handler of SXL file
                obj - SxlObject instance
                indent - current indention within SXL file
            """
            # sort parameters according to attrs
            for parName in obj.attr_list:
                if parName in obj.attrs.keys():
                    parValue = obj.get_attr(parName)
                    f.write(SPACE * indent + "{:7} ".format(parName))
                    if type(parValue) is list and len(parValue) == 2:
                        # targets 'pos' fields
                        f.write(":".join(str(i) for i in parValue) + NEWLINE)
                    elif not isinstance(parValue, str):
                        f.write(str(parValue) + NEWLINE)
                    elif SPACE in parValue:
                        # handle 'desc' fields with spaces
                        f.write("{" + parValue + "}" + NEWLINE)
                    else:
                        f.write(parValue + NEWLINE)

        def add_level(f, obj, indent, sxl_type, hierarchy):
            """Iterate through full hierarchical SXL level and write to SXL file.
            Args:
                f - file handler
                obj - SXL object of hierarchical level
                indent - current indentation level
                hierarchy - description of SXL hierarchy to save
            """
            for level in getattr(hierarchy, sxl_type):
                sxl_type = getattr(self.config, level).type
                if obj.num_objects_of_type(sxl_type) > 0:
                    if self.groups:
                        f.write(SPACE * indent + sxl_type + "s {" + NEWLINE)
                    for curr_obj in obj.get_object_type_list(sxl_type):
                        # indentation according to group configuration
                        ind = indent + 2 * int(self.groups)
                        # open new group with current object identifier
                        name = curr_obj.name
                        if SPACE in name:
                            f.write(SPACE * ind + "{" + name + "} {" + NEWLINE)
                        else:
                            f.write(SPACE * ind + name + " {" + NEWLINE)
                        # add object attributes
                        add_attrs(f, curr_obj, indent + 4)
                        # objects
                        if curr_obj.num_objects() > 0:
                            # handle object children
                            add_level(f, curr_obj, indent + 4, sxl_type, hierarchy)
                        # close group with current object identifier
                        f.write(SPACE * ind + "}" + NEWLINE)
                    if self.groups:
                        # grouping: close item type group
                        f.write(SPACE * indent + "}" + NEWLINE)

        # check and create dirname if applicable
        dirname = os.path.dirname(file)
        if dirname != "" and not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(file, "w") as f:
            # add device attributes when available
            if len(self.attrs) > 0:
                f.write(self.config.Dev + " {" + NEWLINE)
                add_attrs(f, self, 4)
                f.write("}" + NEWLINE)
            # main SXL definitions
            add_level(f, self, 0, "root", self.config.hierarchy)

    ##################### SXL helper functions #####################
    def findIconTop(self):
        """find the top SXL Icon object of the provided hierarchy, if known."""
        iconList = self.get_objects_of_type(self.config.Icon)
        mstList = self.get_objects_of_type(self.config.Mst)
        slvList = self.get_objects_of_type(self.config.Slv)
        if len(iconList) == 0:
            return None
        topIcon = iconList[0]
        lastTopIcon = None
        while lastTopIcon != topIcon:
            lastTopIcon = topIcon
            for m in mstList:
                mName = m.name
                for s in slvList:
                    sName = s.name
                    iconLink = s.get_attr("icon")
                    if iconLink and iconLink == mName:
                        topIcon = s.parent
                        break
                if iconLink and iconLink == mName:
                    break
        return topIcon

    def listIconSlaves(
        self,
        top,
        addr_base=0x00000000,
        sizeBase=0x100000000,
        mask_base=0xFFFFFFFF,
        loc="",
        block_list=None):
        """Partial scan of SXL hierarchy structure."""
        if block_list is None:
            block_list = list()
        for slave in top.get_objects_of_type(self.config.Slv):
            slv_name = slave.name
            slv_id = slv_name
            if "icon" in slave.attrs.keys():
                slv_name = slave.attrs["icon"]
            mask = 0xFFFFFFFF
            if "mask" in slave.attrs.keys():
                mask = int(slave.attrs["mask"], 0)
            addr = int(slave.attrs["addr"], 0)
            size = int(slave.attrs["size"], 0)
            if (addr_base & mask_base) > (addr & mask_base) or \
               (addr_base & mask_base) + sizeBase < \
                                         (addr & mask_base) + size:
                # skip when out of address range
                continue
            addr = (addr & mask_base) | addr_base
            # masters
            for master in self.get_objects_of_type(self.config.Mst):
                mst_root = master.parent
                mst_name = master.name
                if mst_name == slv_name:
                    self.listIconSlaves(
                        mst_root, addr, size, mask, f"{loc}->{slv_id}", block_list
                    )
            # resolve block links of all existing slaves
            if self.config.Block in slave.attrs.keys():
                block_name = slave.attrs[self.config.Block]
                block = self.get_object_of_name(block_name)
                block_addr = -1
                block_size = -1
                if block != None and block.type == self.config.Block:
                    if "size" in block.attrs.keys():
                        block_size = int(block.attrs["size"], 0)
                    block_addr = addr
                # add block to list with properties: name, addr, size, location
                block_list.append([block, block_addr, block_size, f"{loc}->{slv_id}"])
        return block_list

# Read README.md for more info
DEFAULT_SXL_CONFIG = {
    "Root": Sxl.Root,
    "Dev": Sxl.Dev,
    "Block": Sxl.Block,
    "Reg": Sxl.Reg,
    "Sig": Sxl.Sig,
    "Enum": Sxl.Enum,
    "Flag": Sxl.Flag,
    "Icon": Sxl.Icon,
    "Mst": Sxl.Mst,
    "Slv": Sxl.Slv,
    "root_type": {
        "type": Sxl.Root,
        "attrs": ["desc", "name", "project", "version", "date", "author"],
    },
    "block_type": {"type": "block", "attrs": ["desc", "size", "tags"]},
    "reg_type": {
        "type": "register",
        "attrs": ["desc", "addr", "type", "tags"],
    },
    "sig_type": {
        "type": Sxl.Sig,
        "attrs": [
            "desc",
            "addr",
            "pos",
            "mode",
            "type",
            "reset",
            "tags",
        ],
    },
    "enum_type": {"type": Sxl.Enum, "attrs": ["desc", "value", "tags"]},
    "flag_type": {"type": Sxl.Flag, "attrs": ["desc", "pos", "type", "tags"]},
    "icon_type": {"type": Sxl.Icon, "attrs": ["desc", "type", "databits", "mask"]},
    "mst_type": {"type": Sxl.Mst, "attrs": ["desc", "type"]},
    "slv_type": {
        "type": Sxl.Slv,
        "attrs": ["desc", "type", "block", "icon", "addr", "size", "mask"],
    },
    "hierarchy": {
        "device": ["root_type"],
        "root": ["block_type", "icon_type"],
        "block": ["sig_type", "reg_type"],
        "record": ["sig_type"],
        "register": ["sig_type"],
        "signal": ["enum_type", "flag_type"],
        "enum": [],
        "flag": [],
        "intercon": ["mst_type", "slv_type"],
        "master": [],
        "slave": [],
    },
}
