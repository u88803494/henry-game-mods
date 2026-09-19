import struct, sys, threading, pickle, lzma

sys.setrecursionlimit(2_000_000)

BOOL=0x01; I8=0x02; I16=0x03; I32=0x04; I64=0x05
U8=0x06; U16=0x07; U32=0x08; U64=0x09
F32=0x0a; F64=0x0b; COORD_2D=0x0c; COORD_3D=0x0d
UTF16=0x0e; ASCII=0x0f; ANGLE=0x10
BOOL_TRUE=0x12; BOOL_FALSE=0x13
U32_ZERO=0x14; U32_ONE=0x15; U32_BYTE=0x16; U32_16BIT=0x17; U32_24BIT=0x18
I32_ZERO=0x19; I32_BYTE=0x1a; I32_16BIT=0x1b; I32_24BIT=0x1c; F32_ZERO=0x1d
UNKNOWN_21=0x21; UNKNOWN_23=0x23; UNKNOWN_24=0x24; UNKNOWN_25=0x25; UNKNOWN_26=0x26
BOOL_ARRAY=0x41; I8_ARRAY=0x42; I16_ARRAY=0x43; I32_ARRAY=0x44; I64_ARRAY=0x45
U8_ARRAY=0x46; U16_ARRAY=0x47; U32_ARRAY=0x48; U64_ARRAY=0x49
F32_ARRAY=0x4a; F64_ARRAY=0x4b; COORD_2D_ARRAY=0x4c; COORD_3D_ARRAY=0x4d
UTF16_ARRAY=0x4e; ASCII_ARRAY=0x4f; ANGLE_ARRAY=0x50
U32_BYTE_ARRAY=0x56; U32_16BIT_ARRAY=0x57; U32_24BIT_ARRAY=0x58
I32_BYTE_ARRAY=0x5a; I32_16BIT_ARRAY=0x5b; I32_24BIT_ARRAY=0x5c

IS_RECORD_NODE=0x80; HAS_NESTED_BLOCKS=0x40; HAS_NON_OPTIMIZED_INFO=0x20

class Rdr:
    __slots__=('d','pos')
    def __init__(self, d, pos=0):
        self.d=d; self.pos=pos
    def u8(self):
        v=self.d[self.pos]; self.pos+=1; return v
    def i8(self):
        v=self.d[self.pos]; self.pos+=1
        return v-256 if v>=128 else v
    def u16(self):
        v=struct.unpack_from('<H',self.d,self.pos)[0]; self.pos+=2; return v
    def i16(self):
        v=struct.unpack_from('<h',self.d,self.pos)[0]; self.pos+=2; return v
    def u24(self):
        b=self.d[self.pos:self.pos+3]; self.pos+=3
        return b[0]|(b[1]<<8)|(b[2]<<16)
    def i24(self):
        v=self.u24()
        return v-0x1000000 if v & 0x800000 else v
    def u32(self):
        v=struct.unpack_from('<I',self.d,self.pos)[0]; self.pos+=4; return v
    def i32(self):
        v=struct.unpack_from('<i',self.d,self.pos)[0]; self.pos+=4; return v
    def u64(self):
        v=struct.unpack_from('<Q',self.d,self.pos)[0]; self.pos+=8; return v
    def i64(self):
        v=struct.unpack_from('<q',self.d,self.pos)[0]; self.pos+=8; return v
    def f32(self):
        v=struct.unpack_from('<f',self.d,self.pos)[0]; self.pos+=4; return v
    def f64(self):
        v=struct.unpack_from('<d',self.d,self.pos)[0]; self.pos+=8; return v
    def bytes(self,n):
        v=self.d[self.pos:self.pos+n]; self.pos+=n; return v
    def boolean(self):
        return self.u8()!=0
    def cauleb128(self):
        value=0
        byte=self.u8()
        while byte & 0x80:
            value=(value<<7) | (byte & 0x7f)
            byte=self.u8()
        value=(value<<7) | (byte & 0x7f)
        return value

def read_node(r, is_root, record_names, str8, str16):
    next_byte = r.u8()
    if next_byte & IS_RECORD_NODE:
        has_noi = bool(next_byte & HAS_NON_OPTIMIZED_INFO) or is_root
        if has_noi:
            name_index = r.u16()
            version = r.u8()
        else:
            version = (next_byte & 0x1E) >> 1
            name_index = ((next_byte & 1) << 8) + r.u8()
        name = record_names[name_index]

        block_size = r.cauleb128()
        has_nested = bool(next_byte & HAS_NESTED_BLOCKS)
        group_count = r.cauleb128() if has_nested else 1
        final_block_offset = r.pos + block_size

        groups=[]
        for _ in range(group_count):
            if has_nested:
                entry_size = r.cauleb128()
                final_entry_offset = r.pos + entry_size
            else:
                final_entry_offset = final_block_offset
            node_list=[]
            while r.pos < final_entry_offset:
                node_list.append(read_node(r, False, record_names, str8, str16))
            if r.pos != final_entry_offset:
                raise ValueError(f'entry size mismatch at {r.pos} != {final_entry_offset} in {name}')
            groups.append(node_list)
        if r.pos != final_block_offset:
            raise ValueError(f'block size mismatch at {r.pos} != {final_block_offset} in {name}')

        return {'_r': name, '_v': version, '_g': groups}

    t = next_byte
    if t==BOOL: return r.boolean()
    if t==I8: return r.i8()
    if t==I16: return r.i16()
    if t==I32: return r.i32()
    if t==I64: return r.i64()
    if t==U8: return r.u8()
    if t==U16: return r.u16()
    if t==U32: return r.u32()
    if t==U64: return r.u64()
    if t==F32: return r.f32()
    if t==F64: return r.f64()
    if t==COORD_2D: return (r.f32(), r.f32())
    if t==COORD_3D: return (r.f32(), r.f32(), r.f32())
    if t==UTF16:
        idx=r.u32()
        return str16[idx]
    if t==ASCII:
        idx=r.u32()
        return str8[idx]
    if t==ANGLE: return r.i16()
    if t==BOOL_TRUE: return True
    if t==BOOL_FALSE: return False
    if t==U32_ZERO: return 0
    if t==U32_ONE: return 1
    if t==U32_BYTE: return r.u8()
    if t==U32_16BIT: return r.u16()
    if t==U32_24BIT: return r.u24()
    if t==I32_ZERO: return 0
    if t==I32_BYTE: return r.i8()
    if t==I32_16BIT: return r.i16()
    if t==I32_24BIT: return r.i24()
    if t==F32_ZERO: return 0.0
    if t==UNKNOWN_21: return ('u21', r.u32())
    if t==UNKNOWN_23: return ('u23', r.u8())
    if t==UNKNOWN_24: return ('u24', r.u16())
    if t==UNKNOWN_25: return ('u25', r.u32())
    if t==UNKNOWN_26:
        data=bytearray()
        fb = r.u8(); data.append(fb)
        if fb % 8 == 0 and fb != 0:
            data.extend(r.bytes(fb))
        else:
            data.extend(r.bytes(7))
        save_pos = r.pos
        lb = r.u8()
        if lb != 0x9C:
            r.pos = save_pos
        return ('u26', bytes(data))

    if t==BOOL_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.boolean())
        return out
    if t==I8_ARRAY:
        size=r.cauleb128(); return list(r.bytes(size))
    if t==U8_ARRAY:
        size=r.cauleb128(); return bytes(r.bytes(size))
    if t==I16_ARRAY or t==ANGLE_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.i16())
        return out
    if t==U16_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.u16())
        return out
    if t==I32_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.i32())
        return out
    if t==U32_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.u32())
        return out
    if t==I64_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.i64())
        return out
    if t==U64_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.u64())
        return out
    if t==F32_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.f32())
        return out
    if t==F64_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.f64())
        return out
    if t==COORD_2D_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append((r.f32(), r.f32()))
        return out
    if t==COORD_3D_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append((r.f32(), r.f32(), r.f32()))
        return out
    if t==UTF16_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end:
            idx=r.u32(); out.append(str16[idx])
        return out
    if t==ASCII_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end:
            idx=r.u32(); out.append(str8[idx])
        return out
    if t==U32_BYTE_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.u8())
        return out
    if t==U32_16BIT_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.u16())
        return out
    if t==U32_24BIT_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.u24())
        return out
    if t==I32_BYTE_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.i8())
        return out
    if t==I32_16BIT_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.i16())
        return out
    if t==I32_24BIT_ARRAY:
        size=r.cauleb128(); end=r.pos+size; out=[]
        while r.pos<end: out.append(r.i24())
        return out

    raise ValueError(f'unknown node type marker 0x{t:02x} at pos {r.pos-1}')


def parse_esf_bytes(d, depth=0):
    magic = d[:4]
    if magic != b'\xca\xab\x00\x00':
        raise ValueError(f'unexpected magic {magic!r}')
    unk, ts, strtab_off = struct.unpack_from('<III', d, 4)
    nodes_offset = 16

    p = strtab_off
    n = struct.unpack_from('<H', d, p)[0]; p+=2
    record_names=[]
    for _ in range(n):
        l = struct.unpack_from('<H', d, p)[0]; p+=2
        record_names.append(d[p:p+l].decode('utf-8')); p+=l

    n = struct.unpack_from('<I', d, p)[0]; p+=4
    str16={}
    for _ in range(n):
        l = struct.unpack_from('<H', d, p)[0]; p+=2
        s = d[p:p+l*2].decode('utf-16-le'); p+=l*2
        idx = struct.unpack_from('<I', d, p)[0]; p+=4
        str16[idx]=s

    n = struct.unpack_from('<I', d, p)[0]; p+=4
    str8={}
    for _ in range(n):
        l = struct.unpack_from('<H', d, p)[0]; p+=2
        s = d[p:p+l].decode('utf-8'); p+=l
        idx = struct.unpack_from('<I', d, p)[0]; p+=4
        str8[idx]=s

    if p != len(d):
        print(f'  [depth {depth}] WARNING: string tables ended at {p}, file len {len(d)}', file=sys.stderr)

    r = Rdr(d, nodes_offset)
    root = read_node(r, True, record_names, str8, str16)
    if r.pos != strtab_off:
        raise ValueError(f'node tree ended at {r.pos}, expected {strtab_off}')

    print(f'  [depth {depth}] parsed OK: {len(d)} bytes, root={root["_r"]!r}, {len(record_names)} record names, {len(str8)} ascii, {len(str16)} utf16', file=sys.stderr)

    # check for compressed nested ESF: last child of first group of root must be COMPRESSED_DATA record
    g0 = root['_g'][0]
    if g0 and isinstance(g0[-1], dict) and g0[-1].get('_r') == 'COMPRESSED_DATA':
        cnode = g0[-1]
        cg0 = cnode['_g'][0]
        cdata = cg0[0]            # U8Array: raw compressed payload
        hnode = cg0[1]            # Record: COMPRESSED_DATA_INFO
        assert hnode['_r'] == 'COMPRESSED_DATA_INFO'
        hg0 = hnode['_g'][0]
        len_val = hg0[0]          # U32
        magic5 = hg0[1]           # U8Array (5 bytes)
        assert isinstance(cdata, bytes) and isinstance(magic5, bytes) and len(magic5) == 5

        # magic5 = LZMA1 props(1)+dictsize(4); len_val = uncompressed size (32-bit, stored separately).
        # Standard LZMA_ALONE header = props(1) + dictsize(4) + uncompsize(8, LE) ; body is raw cdata.
        mdata = magic5 + struct.pack('<Q', len_val) + cdata
        print(f'  [depth {depth}] found COMPRESSED_DATA: cdata={len(cdata)} bytes, uncompressed_size={len_val}, reconstructing LZMA_ALONE stream ({len(mdata)} bytes header+body)...', file=sys.stderr)

        dec = lzma.decompress(mdata, format=lzma.FORMAT_ALONE)
        print(f'  [depth {depth}] decompressed to {len(dec)} bytes, recursing...', file=sys.stderr)
        return parse_esf_bytes(dec, depth+1)

    return root


def _run(path, out_pickle):
    d = open(path, 'rb').read()
    root = parse_esf_bytes(d)
    with open(out_pickle, 'wb') as f:
        pickle.dump(root, f, protocol=4)
    print('OK, saved to', out_pickle, file=sys.stderr)

if __name__=='__main__':
    path = sys.argv[1]
    out = sys.argv[2]
    err=[None]
    def target():
        try:
            _run(path, out)
        except Exception as e:
            import traceback; traceback.print_exc()
            err[0]=e
    try:
        threading.stack_size(1024*1024*1024)
    except (ValueError, RuntimeError) as e:
        print('stack_size warn:', e, file=sys.stderr)
    th = threading.Thread(target=target)
    th.start()
    th.join()
    if err[0]:
        sys.exit(1)
