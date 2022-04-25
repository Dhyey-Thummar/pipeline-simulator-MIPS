###
# File to store simulator global variables
###

# Simulator flags for the history board at the end
ran = {'IF': (0, 0), 'ID': (0, 0), 'EX': (0, 0), 'MEM': (0, 0), 'WB': (0, 0)}
wasIdle = {'IF': False, 'ID': False, 'EX': False, 'MEM': False, 'WB': False}

# Dictionaries for easier processing
rTypeWords = { 'add': 0b100000, 'sub': 0b100010, 'and': 0b100100,  'or': 0b100101,
               'sll': 0b000000, 'srl': 0b000010, 'xor': 0b100110, 'nor': 0b100111,
              'mult': 0b011000, 'div': 0b011001}
rTypeBins = {v: k for k, v in rTypeWords.items()}
regNames = ['$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3',
              '$t0', '$t1', '$t2', '$t3', '$t4', '$t5', '$t6', '$t7',
              '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
              '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra']

# Data Memory size, can be changed to any multiple of 4
DATA_SIZE = 16

# Error Signals
EINST = -1
EARG = -2
EFLOW = -3
ERROR = [EINST, EARG, EFLOW]

# Enable or disable hazard protections
data_hzd = True
ctrl_hzd = True

# Forwarding+Hazard Units helper variables
outFwdA = 0
outFwdB = 0

###
# File to store simulation registers, control signals and memory
###

# Program Counter
PC = 0

# Instruction Memory
INST = []

# Registers
REGS = [0 for i in range(32)]

# Data Memory
DATA = [0 for i in range(DATA_SIZE)]

# Pipeline Registers
IF_ID = {'NPC': 0, 'IR': 0}
ID_EX = {'NPC': 0, 'A': 0, 'B': 0, 'RT': 0, 'RD': 0, 'IMM': 0, 'RS': 0}
EX_MEM = {'BR_TGT': 0, 'ZERO': 0, 'ALU_OUT': 0, 'B': 0, 'RD': 0}
MEM_WB = {'LMD': 0, 'ALU_OUT': 0, 'RD': 0}

# Control Signals
ID_EX_CTRL = {'REG_DST': 0, 'ALU_SRC': 0, 'MEM_TO_REG': 0, 'REG_WRITE': 0,
              'MEM_READ': 0, 'MEM_WRITE': 0, 'BRANCH': 0, 'ALU_OP': 0}
EX_MEM_CTRL = {'MEM_READ': 0, 'MEM_WRITE': 0, 'BRANCH': 0, 'MEM_TO_REG': 0, 'REG_WRITE': 0}
MEM_WB_CTRL = {'MEM_TO_REG': 0, 'REG_WRITE': 0}

# Forwarding Unit Signals
FWD = {'PC_WRITE': 1, 'IF_ID_WRITE': 1, 'FWD_A': 0, 'FWD_B': 0, 'STALL': 0}

# Convert from string to int
def encode(inst):
    inst = inst.replace(',', '') # Ignore commas

    # Replace register names with its index
    for i in range(len(regNames)):
        inst = inst.replace(regNames[i], str(i))
    inst = inst.replace('$', '') # $0, $4, $7, etc.

    inst = inst.split()

    out = EINST
    if inst[0] in rTypeWords: # R-Type
        out = 0b000000 << 5

        if inst[0] == 'sll' or inst[0] == 'srl':
            try:
                rd, rt, shamt = [int(i, 0) for i in inst[1:]] # Accepts any base (e.g. 0b, 0o, 0x)
            except:
                return EARG # Not correct number of arguments

            # Check for under/overflow
            nrd, nrt, nshamt = rd&0x1F, rt&0x1F, shamt&0x1F
            if [nrd, nrt, nshamt] != [rd, rt, shamt]:
                return EFLOW
            rd, rt, shamt = nrd, nrt, nshamt

            # Encode
            out |= rt
            out <<= 5
            out |= rd
            out <<= 5
            out |= shamt
            out <<= 6
            out |= rTypeWords[inst[0]]

        else: # R-Types other than sll/srl
            try:
                rd, rs, rt = [int(i, 0) for i in inst[1:]] # Accepts any base (e.g. 0b, 0o, 0x)
            except:
                return EARG # Not correct number of arguments

            # Check for under/overflow
            nrd, nrs, nrt = rd&0x1F, rs&0x1F, rt&0x1F
            if [nrd, nrs, nrt] != [rd, rs, rt]:
                return EFLOW
            rd, rs, rt = nrd, nrs, nrt

            # Encode
            out |= rs
            out <<= 5
            out |= rt
            out <<= 5
            out |= rd
            out <<= 11
            out |= rTypeWords[inst[0]]

    elif inst[0] == 'lw' or inst[0] == 'sw':
        opcode = {'lw': 0b100011, 'sw': 0b101011}
        out = opcode[inst[0]] << 5

        try:
            inst[2] = inst[2].split('(')
            inst[2:] = inst[2][0], inst[2][1][:-1]

            rt, offset, rs = [int(i, 0) for i in inst[1:]] # Accepts any base (e.g. 0b, 0o, 0x)
        except:
            return EARG # Not correct number of arguments

        # Check for under/overflow
        nrt, nrs, noffset = rt&0x1F, rs&0x1F, offset&0xFFFF
        if [nrt, nrs, noffset] != [rt, rs, offset]:
            return EFLOW
        rt, rs, offset = nrt, nrs, noffset

        # Encode
        out |= rs
        out <<= 5
        out |= rt
        out <<= 16
        out |= offset

    elif inst[0] == 'beq':
        out = 0b000100 << 5

        try:
            rs, rt, offset = [int(i, 0) for i in inst[1:]] # Accepts any base (e.g. 0b, 0o, 0x)
        except:
            return EARG # Not correct number of arguments

        # Check for under/overflow
        nrs, nrt, noffset = rs&0x1F, rt&0x1F, offset&0xFFFF
        if [nrs, nrt, noffset] != [rs, rt, offset]:
            return EFLOW
        rs, rt, offset = nrs, nrt, noffset

        # Encode
        out |= rs
        out <<= 5
        out |= rt
        out <<= 16
        out |= offset

    elif inst[0] == 'addi':
        out = 0b001000 << 5

        try:
            rt, rs, imm = [int(i, 0) for i in inst[1:]] # Accepts any base (e.g. 0b, 0o, 0x)
        except:
            return EARG # Not correct number of arguments

        # Check for under/overflow
        nrt, nrs, nimm = rt&0x1F, rs&0x1F, imm&0xFFFF
        if [nrt, nrs, nimm] != [rt, rs, imm]:
            return EFLOW
        rt, rs, imm = nrt, nrs, nimm

        # Encode
        out |= rs
        out <<= 5
        out |= rt
        out <<= 16
        out |= imm

    return out
 
def readFile(filename):
    content = []
    with open(filename, 'r', encoding='UTF-8') as f:
        for l in f:
            s = l.strip()
            if s:
                content.append(s)

    return content

def printHistory(clkHistory):
    # Convert clkHistory to history board
    history = [[' ' for i in range(len(clkHistory))] for i in range(len(INST))]
    for i in range(len(clkHistory)):
        for exe in clkHistory[i]:
            if exe[2]: # Idle
                history[exe[1][0]][i] = ' '
                history[exe[1][0]][i] = '(' + exe[0] + ')' # Show idle stages
            else:
                history[exe[1][0]][i] = exe[0]

    # Print header and column titles
    print('╔' + '═'*(6*len(clkHistory)) + '╗')
    print('║', end='')
    for i in range(len(clkHistory)):
        print(str(i).center(5), end=' ')
    print('║')
    print('╠' + '═'*(6*len(clkHistory)) + '╣')

    # Print history board
    for i in range(len(history)):
        print('║', end='')
        for j in range(len(history[0])):
            print(history[i][j].center(5), end=' ')
        print('║')
    print('╚' + '═'*(6*len(clkHistory)) + '╝')