''' Example script to create an SXL file '''

import unittest
import os
import sys
from pathlib import Path
sys.path.append("..")
from sxl import Sxl, SxlRoot

class SxlTest(unittest.TestCase):
    def test_generate_sxl_file(self):
        # create the SXL Root
        root = SxlRoot()

        # create a block unit
        block = root.new( Sxl.Block, "TestBlock", dict(size="0x1000", desc="A sample block"))

        # create block signals
        block.new( Sxl.Sig, "Signal1", dict(addr="0x0000", pos="31:0", reset="0xAFFEDEAD", 
                                            desc="32bit read/write signal"))
        block.new( Sxl.Sig, "Signal2", dict(addr="0x0004", pos="15:0", mode="ro", 
                                            desc="16bit read-only signal"))
        block.new( Sxl.Sig, "Signal3", dict(addr="0x0004", pos="31:16", mode="wo", 
                                            desc="16bit write-only signal"))
        sig = block.new( Sxl.Sig, "EnumSignal", dict(addr="0x0008", pos="7:0", mode="rw", 
                                                     type="enum", desc="8bit enum signal"))
        sig.new( Sxl.Enum, "Enum1", dict(value=0, desc="Some enum with value=0"))
        sig.new( Sxl.Enum, "Enum2", dict(value=5, desc="Some enum with value=5"))
        sig.new( Sxl.Enum, "Enum3", dict(value=42, desc="Some enum with value=42"))
        sig = block.new( Sxl.Sig, "RWFlagSignal", dict(addr="0x0009", pos="3:0", mode="rw", 
                                                       type="flag", desc="8bit flag signal"))
        sig.new( Sxl.Flag, "Flag0", dict(pos=0, desc="Some flag at position 0"))
        sig.new( Sxl.Flag, "Flag1", dict(pos=1, desc="Some flag at position 1"))
        sig.new( Sxl.Flag, "Flag2", dict(pos=2, desc="Some flag at position 2"))
        sig = block.new( Sxl.Sig, "ROFlagSignal", dict(addr="0x0009", pos="7:4", mode="ro", 
                                                       type="flag", desc="8bit read-only flag signal"))
        sig.new( Sxl.Flag, "RO Flag 0", dict(pos=0, desc="Some flag at position 0"))
        sig.new( Sxl.Flag, "RO Flag 1", dict(pos=1, desc="Some flag at position 1"))
        sig.new( Sxl.Flag, "RO Flag 2", dict(pos=2, desc="Some flag at position 2"))

        # create register signals
        reg = block.new( Sxl.Reg, "Reg1", dict(addr="0x0008", desc="Register carrier for signal"))
        reg.new( Sxl.Sig, "RegSigRW", dict(pos="7:0", mode="rw", desc="RW Signal of a register"))
        reg.new( Sxl.Sig, "RegSigRO", dict(pos="15:8", mode="ro", desc="RO Signal of a register"))
        reg.new( Sxl.Sig, "RegSigWO", dict(pos="29:24", mode="wo", desc="WO Signal of a register"))
        reg.new( Sxl.Sig, "RegSigBit", dict(pos="30", mode='rw', desc="Bit Signal of a register"))
        reg.new( Sxl.Sig, "RegSigT", dict(pos="31", mode='t', desc="Signal of a register"))

        reg = block.new( Sxl.Reg, "Reg2", dict(addr="0x000C", desc="Register carrier for enum/flag signal"))
        sig1 = reg.new( Sxl.Sig, "RegEnumSig", dict(pos="5:0", type="enum", reset="42", 
                                                    desc="Enums Signal of a register"))
        sig1.new( Sxl.Enum, "Enum1", dict(value=0, desc="Some enum with value=0"))
        sig1.new( Sxl.Enum, "Enum2", dict(value=5, desc="Some enum with value=5"))
        sig1.new( Sxl.Enum, "Enum3", dict(value=42, desc="Some enum with value=42"))
        sig2 = reg.new( Sxl.Sig, "RegFlagSig", dict(pos="18:16", reset=5, type="flag", 
                                                    desc="Flags Signal of a register"))
        sig2.new( Sxl.Flag, "Flag0", dict(pos=0, desc="Some flag at position 0"))
        sig2.new( Sxl.Flag, "Flag1", dict(pos=1, desc="Some flag at position 1"))
        sig2.new( Sxl.Flag, "Flag2", dict(pos=2, desc="Some flag at position 2"))

        # different register types
        reg8 = block.new( Sxl.Reg, "ByteReg", dict(addr="0x0010", type='byte', desc="Byte register"))
        reg8.new( Sxl.Sig, "ByteSig", dict(pos="7:0", mode="rw", reset="0x58", desc="Byte Signal R/W"))
        reg16 = block.new( Sxl.Reg, "WordReg", dict(addr="0x0012", type='word', desc="Word register"))
        reg16.new( Sxl.Sig, "WordSig", dict(pos="15:0", mode="rw", reset="0x589C", desc="Word Signal R/W"))
        reg32 = block.new( Sxl.Reg, "DwordReg", dict(addr="0x0014", type='dword', desc="DWord register"))
        reg32.new( Sxl.Sig, "DwordMsb", dict(pos="31", mode="rw", reset="0", desc="Dword MSB Flag R/W"))
        reg32.new( Sxl.Sig, "DwordSig", dict(pos="30:0", mode="rw", reset="0x58426540", desc="Dword Signal R/W"))

        # fixed point example
        regT = block.new( Sxl.Reg, "TypeReg", dict(addr="0x0018", desc="TypeReg"))
        regT.new( Sxl.Sig, "SigU8",   dict(pos="7:0",   type="U8",   reset="158", desc="Signal with type U8"))
        regT.new( Sxl.Sig, "SigU4.4", dict(pos="15:8",  type="U4.4", reset="158", desc="Signal with type U4.4"))
        regT.new( Sxl.Sig, "SigS8",   dict(pos="23:16", type="S8",   reset="158", desc="Signal with type S8"))
        regT.new( Sxl.Sig, "SigS4.4", dict(pos="31:24", type="S4.4", reset="158", desc="Signal with type S4.4"))

        # seperator added - tweak to insert visual seperators, must be added as icon too!
        sep_name = "===== Seperator ====="
        root.new( Sxl.Block, sep_name, dict(size="0"))

        # tag trial
        block = root.new( Sxl.Block, "TaggedBlock", dict(size="0x1000", desc="A sample block", tags="test"))
        block.new( Sxl.Sig, "DiagnosisSignal", dict(addr="0x0020", mode="ro", pos="15:0", 
                                                    desc="Signal marked with tag 'diagnosis'",
                                                    tags="diagnosis"))
        block.new( Sxl.Sig, "Test42Signal", dict(addr="0x0022", mode="ro", pos="15:0", 
                                                    desc="Signal marked with tags 'diagnosis' and '42'",
                                                    tags="diagnosis 42"))

        # create icon for address offset
        icon = root.new( Sxl.Icon, "top", dict(desc = "toplevel"))
        icon.new( Sxl.Mst, "top", dict(desc = "toplevel master"))
        icon.new( Sxl.Slv, "TestBlock", dict(addr="0x34000000", size="0x1000", block="TestBlock", 
                                             desc="toplevel slave"))
        icon.new( Sxl.Slv, sep_name, dict(addr="0", size="0", block=sep_name))
        icon.new( Sxl.Slv, "TaggedBlock", dict(addr="0x34001000", size="0x1000", block="TaggedBlock"))

        # create sample table
        # method 1
        table = block.new(Sxl.Table, "pwl0", dict(desc="text PWL mapping x to y", addr="0x40", length="16", stride="0x08", tags="pwl0"))
        table.new(Sxl.Column, "x", dict(desc="PWL input", addr="0x00", pos="31:0", type="U32"))
        table.new(Sxl.Column, "y", dict(desc="PWL output", addr="0x04", pos="31:0", type="U16.16"))
        # method 2
        table = block.new(Sxl.Table, "pwl1", dict(desc="text PWL mapping x to y", addr="0xC0", tags="pwl1"))
        table.new(Sxl.Column, "x", dict(desc="PWL input", addr="0x00", pos="31:0", type="U32"))
        table.new(Sxl.Column, "y", dict(desc="PWL output", addr="0x04", pos="31:0", type="U16.16"))
        # additional details about rows and signals of rows
        for i in range(16):
            row = table.new(Sxl.Row, f"row{i}", dict(addr=f"0x{8*i:02X}", desc=f"Custom row {i}"))
            row.new(Sxl.Sig, f"x{i}", dict(desc=f"PWL input {i}", addr="0x00", pos="31:0", type="U32"))
            row.new(Sxl.Sig, f"y{i}", dict(desc=f"PWL output {i}", addr="0x04", pos="31:0", type="U16.16"))

        # save sxl file
        sxl_path = Path(os.path.dirname(__file__)) / "test.sxl"
        root.save(sxl_path)
        print(f'SXL file {sxl_path} generated.')

if __name__ == '__main__':
    unittest.main()
