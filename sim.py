#######################################################################################################
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

############################################################################################################
# Now py down
############################################################################################################
###
# File to store simulation registers, control signals and memory
###

#import G_UTL

# Program Counter
global PC
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

###################################################################################
# Now py down
###################################################################################
# Supported Instructions:
# add $d, $s, $t     # 000000|rs[5]|rt[5]|rd[5]|00000|100000 # rd = rs + rt
# sub $d, $s, $t     # 000000|rs[5]|rt[5]|rd[5]|00000|100010 # rd = rs - rt
# and $d, $s, $t     # 000000|rs[5]|rt[5]|rd[5]|00000|100100 # rd = rs & rt
# or $d, $s, $t      # 000000|rs[5]|rt[5]|rd[5]|00000|100101 # rd = rs | rt
# xor $d, $s, $t     # 000000|rs[5]|rt[5]|rd[5]|00000|100110 # rd = rs ^ rt
# nor $d, $s, $t     # 000000|rs[5]|rt[5]|rd[5]|00000|100111 # rd = ~(rs | rt)
# mult $d, $s, $t    # 000000|rs[5]|rt[5]|rd[5]|00000|011000 # rd = rs * rt
# div $d, $s, $t     # 000000|rs[5]|rt[5]|rd[5]|00000|011001 # rd = rs // rt
# sll $d, $t, shamt  # 000000|00000|rt[5]|rd[5]|shamt|000000 # rd = rt << shamt
# srl $d, $t, shamt  # 000000|00000|rt[5]|rd[5]|shamt|000010 # rd = rt >> shamt
# lw $t, offset($s)  # 100011|rs[5]|rt[5]|     offset[16]    # rt = mem(rs + offset)
# sw $t, offset($s)  # 101011|rs[5]|rt[5]|     offset[16]    # mem(rs + offset) = rt
# beq $s, $t, offset # 000100|rs[5]|rt[5]|     offset[16]    # if rs == rt: advance_pc(offset << 2))
# addi $t, $s, imm   # 001000|rs[5]|rt[5]|      imm[16]      # rt = rs + imm

#import G_MEM, G_UTL

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

# Convert from int to string
def decode(inst):
    inst = f'{inst:032b}'

    out = ''
    opcode = int(inst[0:6], 2)
    rs, rt = int(inst[6:11], 2), int(inst[11:16], 2)
    last16 = inst[16:32]

    if opcode == 0b000000: # R-Type
        rd, aluOp = int(last16[0:5], 2), int(last16[10:16], 2)
        
        if aluOp == rTypeWords['sll'] or aluOp == rTypeWords['srl']:
            shamt = int(last16[5:10], 2)
            out = f'{rTypeBins[aluOp]} {regNames[rd]}, {regNames[rt]}, {shamt}'
        else:
            out = f'{rTypeBins[aluOp]} {regNames[rd]}, {regNames[rs]}, {regNames[rt]}'
    elif opcode == 0b100011 or opcode == 0b101011: # lw/sw
        if opcode == 0b100011:
            out = 'lw'
        elif opcode == 0b101011:
            out = 'sw'

        out += f' {regNames[rt]}, {int(last16, 2)}({regNames[rs]})'
    elif opcode == 0b000100: # beq
        out = f'beq {regNames[rs]}, {regNames[rt]}, {int(last16, 2)}'
    elif opcode == 0b001000: # addi
        out = f'addi {regNames[rt]}, {regNames[rs]}, {int(last16, 2)}'

    return out

##########################################################################
# py down
##########################################################################

#import G_MEM, G_UTL

# Control Unit ROM
# RegDst, ALUSrc, MemToReg, RegWrite, MemRead, MemWrite, Branch, AluOp
ctrl = {0b000000: (0b1, 0b0, 0b0, 0b1, 0b0, 0b0, 0b0, 0b10), # R-Type
        0b100011: (0b0, 0b1, 0b1, 0b1, 0b1, 0b0, 0b0, 0b00), # lw
        0b101011: (0b0, 0b1, 0b0, 0b0, 0b0, 0b1, 0b0, 0b00), # sw
        0b000100: (0b0, 0b0, 0b0, 0b0, 0b0, 0b0, 0b1, 0b01), # beq
        0b001000: (0b0, 0b1, 0b0, 0b1, 0b0, 0b0, 0b0, 0b00)} # addi

def EX_fwd():
    # Forwarding Unit
    if MEM_WB_CTRL['REG_WRITE'] == 1 and MEM_WB['RD'] != 0 and MEM_WB['RD'] == ID_EX['RS'] and (EX_MEM['RD'] != ID_EX['RS'] or EX_MEM_CTRL['REG_WRITE'] == 0):
        FWD['FWD_A'] = 1
    elif EX_MEM_CTRL['REG_WRITE'] == 1 and EX_MEM['RD'] != 0 and EX_MEM['RD'] == ID_EX['RS']:
        FWD['FWD_A'] = 2
    else:
        FWD['FWD_A'] = 0

    if MEM_WB_CTRL['REG_WRITE'] == 1 and MEM_WB['RD'] != 0 and MEM_WB['RD'] == ID_EX['RT'] and (EX_MEM['RD'] != ID_EX['RT'] or EX_MEM_CTRL['REG_WRITE'] == 0):
        FWD['FWD_B'] = 1
    elif EX_MEM_CTRL['REG_WRITE'] == 1 and EX_MEM['RD'] != 0 and EX_MEM['RD'] == ID_EX['RT']:
        FWD['FWD_B'] = 2
    else:
        FWD['FWD_B'] = 0

    # FwdA Multiplexer
    if FWD['FWD_A'] == 0 or not data_hzd:
        outFwdA = ID_EX['A']
    elif FWD['FWD_A'] == 1:
        if MEM_WB_CTRL['MEM_TO_REG'] == 1:
            outFwdA = MEM_WB['LMD']
        else:
            outFwdA = MEM_WB['ALU_OUT']
    elif FWD['FWD_A'] == 2:
        outFwdA = EX_MEM['ALU_OUT']

    # FwdB Multiplexer
    if FWD['FWD_B'] == 0 or not data_hzd:
        outFwdB = ID_EX['B']
    elif FWD['FWD_B'] == 1:
        # MemToReg Multiplexer
        if MEM_WB_CTRL['MEM_TO_REG'] == 1:
            outFwdB = MEM_WB['LMD']
        else:
            outFwdB = MEM_WB['ALU_OUT']
    elif FWD['FWD_B'] == 2:
        outFwdB = EX_MEM['ALU_OUT']

def ID_hzd():
    # Hazard Unit
    if_id_rs = (IF_ID['IR'] & 0x03E00000) >> 21 # IR[25..21]
    if_id_rt = (IF_ID['IR'] & 0x001F0000) >> 16 # IR[20..16]

    if ID_EX_CTRL['MEM_READ'] == 1 and (ID_EX['RT'] == if_id_rs or ID_EX['RT'] == if_id_rt) and data_hzd:
        FWD['PC_WRITE'] = 0
        FWD['IF_ID_WRITE'] = 0
        FWD['STALL'] = 1
    elif (ID_EX_CTRL['BRANCH'] == 1 or EX_MEM_CTRL['BRANCH'] == 1) and ctrl_hzd:
        FWD['IF_ID_WRITE'] = 0
        FWD['STALL'] = 1
    else:
        FWD['PC_WRITE'] = 1
        FWD['IF_ID_WRITE'] = 1
        FWD['STALL'] = 0



def IF():
    global PC
    # Grab instruction from memory array
    try:
        curInst = INST[PC//4]
    except IndexError:
        curInst = 0

    # Set simulator flags
    ran['IF'] = (0, 0) if FWD['STALL'] == 1 else (PC//4, curInst)
    wasIdle['IF'] = (FWD['STALL'] == 1)

    if FWD['IF_ID_WRITE'] == 1 or not data_hzd:
        # Set IF/ID.NPC
        IF_ID['NPC'] = PC + 4

        # Set IF/ID.IR
        IF_ID['IR'] = curInst

    if FWD['PC_WRITE'] == 1 or not data_hzd:
        # Set own PC (PC Multiplexer)
        if EX_MEM['ZERO'] == 1 and EX_MEM_CTRL['BRANCH'] == 1:
            PC = EX_MEM['BR_TGT']
        elif FWD['STALL'] != 1:
            PC = PC + 4

def ID():
    # Set simulator flags
    ran['ID'] = (0, 0) if FWD['STALL'] == 1 else ran['IF']
    wasIdle['ID'] = (FWD['STALL'] == 1)

    if FWD['STALL'] == 1:
        # Stall the pipeline, adding a bubble
        ID_EX_CTRL['REG_DST'] = 0
        ID_EX_CTRL['ALU_SRC'] = 0
        ID_EX_CTRL['MEM_TO_REG'] = 0
        ID_EX_CTRL['REG_WRITE'] = 0
        ID_EX_CTRL['MEM_READ'] = 0
        ID_EX_CTRL['MEM_WRITE'] = 0
        ID_EX_CTRL['BRANCH'] = 0
        ID_EX_CTRL['ALU_OP'] = 0
    else:
        # Set Control of ID/EX (Control Unit)
        opcode = (IF_ID['IR'] & 0xFC000000) >> 26 # IR[31..26]
        ID_EX_CTRL['REG_DST'] = ctrl[opcode][0]
        ID_EX_CTRL['ALU_SRC'] = ctrl[opcode][1]
        ID_EX_CTRL['MEM_TO_REG'] = ctrl[opcode][2]
        ID_EX_CTRL['REG_WRITE'] = ctrl[opcode][3]
        ID_EX_CTRL['MEM_READ'] = ctrl[opcode][4]
        ID_EX_CTRL['MEM_WRITE'] = ctrl[opcode][5]
        ID_EX_CTRL['BRANCH'] = ctrl[opcode][6]
        ID_EX_CTRL['ALU_OP'] = ctrl[opcode][7]

    # Set ID/EX.NPC
    ID_EX['NPC'] = IF_ID['NPC']

    # Set ID/EX.A
    reg1 = (IF_ID['IR'] & 0x03E00000) >> 21 # IR[25..21]
    ID_EX['A'] = REGS[reg1]

    # Set ID/EX.B
    reg2 = (IF_ID['IR'] & 0x001F0000) >> 16 # IR[20..16]
    ID_EX['B'] = REGS[reg2]

    # Set ID/EX.RT
    ID_EX['RT'] = (IF_ID['IR'] & 0x001F0000) >> 16 # IR[20..16]

    # Set ID/EX.RD
    ID_EX['RD'] = (IF_ID['IR'] & 0x0000F800) >> 11 # IR[15..11]

    # Set ID/EX.Imm (Sign Extend)
    imm = (IF_ID['IR'] & 0x0000FFFF) >> 0 # IR[15..0]
    ID_EX['IMM'] = imm

    # Set ID/EX.RS
    ID_EX['RS'] = (IF_ID['IR'] & 0x03E00000) >> 21 # IR[25..21]

def EX():
    # Set simulator flags
    ran['EX'] = ran['ID']
    wasIdle['EX'] = False

    # Set Control of EX/MEM based on Control of ID/EX
    EX_MEM_CTRL['MEM_TO_REG'] = ID_EX_CTRL['MEM_TO_REG']
    EX_MEM_CTRL['REG_WRITE'] = ID_EX_CTRL['REG_WRITE']
    EX_MEM_CTRL['BRANCH'] = ID_EX_CTRL['BRANCH']
    EX_MEM_CTRL['MEM_READ'] = ID_EX_CTRL['MEM_READ']
    EX_MEM_CTRL['MEM_WRITE'] = ID_EX_CTRL['MEM_WRITE']

    # Set EX/MEM.BrTgt (Shift Left 2)
    EX_MEM['BR_TGT'] = ID_EX['NPC'] + (ID_EX['IMM'] << 2)

    # Set internal ALU source A
    aluA = outFwdA

    # Set internal ALU source B (B Multiplexer)
    if ID_EX_CTRL['ALU_SRC'] == 1:
        aluB = ID_EX['IMM']
    else:
        aluB = outFwdB

    # Set EX/MEM.Zero (ALU)
    if aluA - aluB == 0:
        EX_MEM['ZERO'] = 1
    else:
        EX_MEM['ZERO'] = 0

    # Set EX/MEM.AluOut (ALU + ALU Control)
    out = 0
    if ID_EX_CTRL['ALU_OP'] == 0: # Add (lw/sw/addi)
        out = aluA + aluB
    elif ID_EX_CTRL['ALU_OP'] == 1: # Sub (beq)
        out = aluA - aluB
    elif ID_EX_CTRL['ALU_OP'] == 2: # R-Type
        funct = ID_EX['IMM'] & 0x0000003F # IR[5..0]
        shamt = ID_EX['IMM'] & 0x000007C0 # IR[10..6]
        if funct == rTypeWords['add']:
            out = aluA + aluB
        elif funct == rTypeWords['sub']:
            out = aluA - aluB
        elif funct == rTypeWords['and']:
            out = aluA & aluB
        elif funct == rTypeWords['or']:
            out = aluA | aluB
        elif funct == rTypeWords['sll']:
            out = aluA << shamt
        elif funct == rTypeWords['srl']:
            out = aluA >> shamt
        elif funct == rTypeWords['xor']:
            out = aluA ^ aluB
        elif funct == rTypeWords['nor']:
            out = ~(aluA | aluB)
        elif funct == rTypeWords['mult']:
            out = aluA * aluB
        elif funct == rTypeWords['div']:
            out = aluA // aluB
    EX_MEM['ALU_OUT'] = out

    # Set EX/MEM.B
    EX_MEM['B'] = outFwdB

    # Set EX/MEM.RD (RegDst Multiplexer)
    if ID_EX_CTRL['REG_DST'] == 1:
        EX_MEM['RD'] = ID_EX['RD']
    else:
        EX_MEM['RD'] = ID_EX['RT']

def MEM():
    # Set simulator flags
    ran['MEM'] = ran['EX']
    wasIdle['MEM'] = EX_MEM_CTRL['MEM_READ'] != 1 and EX_MEM_CTRL['MEM_WRITE'] != 1

    # Set Control of MEM/WB based on Control of EX/MEM
    MEM_WB_CTRL['MEM_TO_REG'] = EX_MEM_CTRL['MEM_TO_REG']
    MEM_WB_CTRL['REG_WRITE'] = EX_MEM_CTRL['REG_WRITE']

    # Set MEM/WB.LMD (read from Data Memory)
    if EX_MEM_CTRL['MEM_READ'] == 1:
        # The simulation memory might not be big enough
        if EX_MEM['ALU_OUT']//4 < DATA_SIZE:
            MEM_WB['LMD'] = DATA[EX_MEM['ALU_OUT']//4]
        else:
            print('***WARNING***')
            print(f'\tMemory Read at position {EX_MEM["ALU_OUT"]} not executed:')
            print(f'\t\tMemory only has {DATA_SIZE*4} positions.')
            
            try:
                input('Press ENTER to continue execution or abort with CTRL-C. ')
            except KeyboardInterrupt:
                print('Execution aborted.')
                exit()
    
    # Write to Data Memory
    if EX_MEM_CTRL['MEM_WRITE'] == 1:
        # The simulation memory might not be big enough
        if EX_MEM['ALU_OUT']//4 < DATA_SIZE:
            DATA[EX_MEM['ALU_OUT']//4] = EX_MEM['B']
        else:
            print('***WARNING***')
            print(f'\tMemory Write at position {EX_MEM["ALU_OUT"]} not executed:')
            print(f'\t\tMemory only has {DATA_SIZE*4} positions.')
            
            try:
                input('Press ENTER to continue execution or abort with CTRL-C. ')
            except KeyboardInterrupt:
                print('Execution aborted.')
                exit()
    
    # Set MEM/WB.ALUOut
    MEM_WB['ALU_OUT'] = EX_MEM['ALU_OUT']

    # Set MEM/WB.RD
    MEM_WB['RD'] = EX_MEM['RD']

def WB():
    # Set simulator flags
    ran['WB'] = ran['MEM']
    wasIdle['WB'] = MEM_WB_CTRL['REG_WRITE'] != 1 or MEM_WB['RD'] == 0

    # Write to Registers
    if MEM_WB_CTRL['REG_WRITE'] == 1 and MEM_WB['RD'] != 0:
        # MemToReg Multiplexer
        if MEM_WB_CTRL['MEM_TO_REG'] == 1:
            REGS[MEM_WB['RD']] = MEM_WB['LMD']
        else:
            REGS[MEM_WB['RD']] = MEM_WB['ALU_OUT']
##############################################################################
# py
##############################################################################
#import instTranslator
#import G_MEM, G_UTL

def readFile(filename):
    content = []
    with open(filename, 'r', encoding='UTF-8') as f:
        for l in f:
            s = l.strip()
            if s:
                content.append(s)

    return content

# def printFwdAndHazard():
#     print('               ╔═════════════[FORWARDING AND HAZARD UNITS]══════════════╗')
#     if FWD['PC_WRITE'] == 1 and FWD['IF_ID_WRITE'] == 1 and FWD['FWD_A'] == 0 and FWD['FWD_B'] == 0:
#         print('               ║ No action.                                             ║')
#     else:
#         if (FWD['PC_WRITE'] == 0 and FWD['IF_ID_WRITE'] == 0) or (ID_EX_CTRL['BRANCH'] == 1 or EX_MEM_CTRL['BRANCH'] == 1):
#             print('               ║ Stalling (blocking write on PC and IF/ID)...           ║')

#         if FWD['FWD_A'] != 0:
#             print('               ║ FWD_A={} (MEM/WB.ALU_OUT -> A)...                       ║'.format(FWD['FWD_A']))

#         if FWD['FWD_B'] != 0:
#             print('               ║ FWD_B={} (MEM/WB.ALU_OUT -> Mux @ aluB and EX/MEM.B)... ║'.format(FWD['FWD_B']))
#     print('               ╚════════════════════════════════════════════════════════╝')

# def printPipelineRegs():
#     print('╔════════════════════╦═══════════[PIPELINE REGISTERS]══════════╦════════════════════╗')
#     print('║      [IF/ID]       ║      [ID/EX]       ║      [EX/MEM]      ║      [MEM/WB]      ║')
#     print('║════════════════════╬════════════════════╬════════════════════╬════════════════════║')
#     print('║                    ║     MEM_TO_REG=[{}] ║     MEM_TO_REG=[{}] ║     MEM_TO_REG=[{}] ║'.format(ID_EX_CTRL['MEM_TO_REG'], EX_MEM_CTRL['MEM_TO_REG'], MEM_WB_CTRL['MEM_TO_REG']))
#     print('║                    ║      REG_WRITE=[{}] ║      REG_WRITE=[{}] ║      REG_WRITE=[{}] ║'.format(ID_EX_CTRL['REG_WRITE'], EX_MEM_CTRL['REG_WRITE'], MEM_WB_CTRL['REG_WRITE']))
#     print('║                    ║         BRANCH=[{}] ║         BRANCH=[{}] ║                    ║'.format(ID_EX_CTRL['BRANCH'], EX_MEM_CTRL['BRANCH']))
#     print('║                    ║       MEM_READ=[{}] ║       MEM_READ=[{}] ║                    ║'.format(ID_EX_CTRL['MEM_READ'], EX_MEM_CTRL['MEM_READ']))
#     print('║                    ║      MEM_WRITE=[{}] ║      MEM_WRITE=[{}] ║                    ║'.format(ID_EX_CTRL['MEM_WRITE'], EX_MEM_CTRL['MEM_WRITE']))
#     print('║                    ║        REG_DST=[{}] ║                    ║                    ║'.format(ID_EX_CTRL['REG_DST']))
#     print('║                    ║        ALU_SRC=[{}] ║                    ║                    ║'.format(ID_EX_CTRL['ALU_SRC']))
#     print('║                    ║        ALU_OP=[{:02b}] ║                    ║                    ║'.format(ID_EX_CTRL['ALU_OP']))
#     print('╠════════════════════╬════════════════════╬════════════════════╬════════════════════╣')
#     print('║     NPC=[{:08X}] ║     NPC=[{:08X}] ║  BR_TGT=[{:08X}] ║                    ║'.format(IF_ID['NPC'], ID_EX['NPC'], EX_MEM['BR_TGT']))
#     print('║                    ║       A=[{:08X}] ║    ZERO=[{:08X}] ║     LMD=[{:08X}] ║'.format(ID_EX['A'], EX_MEM['ZERO'], MEM_WB['LMD']))
#     print('║      IR=[{:08X}] ║       B=[{:08X}] ║ ALU_OUT=[{:08X}] ║                    ║'.format(IF_ID['IR'], ID_EX['B'], EX_MEM['ALU_OUT']))
#     print('║                    ║      RT=[{:08X}] ║       B=[{:08X}] ║ ALU_OUT=[{:08X}] ║'.format(ID_EX['RT'], EX_MEM['B'], MEM_WB['ALU_OUT']))
#     print('║                    ║      RD=[{:08X}] ║      RD=[{:08X}] ║      RD=[{:08X}] ║'.format(ID_EX['RD'], EX_MEM['RD'], MEM_WB['RD']))
#     print('║                    ║     IMM=[{:08X}] ║                    ║                    ║'.format(ID_EX['IMM']))
#     if data_hzd or ctrl_hzd:
#         print('║                    ║      RS=[{:08X}] ║                    ║                    ║'.format(ID_EX['RS']))
#     print('╚════════════════════╩════════════════════╩════════════════════╩════════════════════╝')

# def printPC():
#     print('                                   ╔════[PC]════╗')
#     print('                                   ║ [{:08X}] ║'.format(PC))
#     print('                                   ╚════════════╝')

# def printInstMem():
#     print('╔═════╦═════════════════════════════[PROGRAM]═══════════╦════════════════════════╗')

#     for i in range(len(INST)):
#         print('║ {:>3} ║ 0x{:08X} = 0b{:032b} ║ {:<22} ║'.format(i*4, INST[i], INST[i], decode(INST[i])))

#     print('╚═════╩═════════════════════════════════════════════════╩════════════════════════╝')

# def printRegMem():
#     print('╔════════════════════╦═══════════════[REGISTERS]═══════════════╦════════════════════╗')
#     print('║ $00[ 0]=[{:08X}] ║ $t0[ 8]=[{:08X}] ║ $s0[16]=[{:08X}] ║ $t8[24]=[{:08X}] ║'.format(REGS[0], REGS[8], REGS[16], REGS[24]))
#     print('║ $at[ 1]=[{:08X}] ║ $t1[ 9]=[{:08X}] ║ $s1[17]=[{:08X}] ║ $t9[25]=[{:08X}] ║'.format(REGS[1], REGS[9], REGS[17], REGS[25]))
#     print('║ $v0[ 2]=[{:08X}] ║ $t2[10]=[{:08X}] ║ $s2[18]=[{:08X}] ║ $k0[26]=[{:08X}] ║'.format(REGS[2], REGS[10], REGS[18], REGS[26]))
#     print('║ $v1[ 3]=[{:08X}] ║ $t3[11]=[{:08X}] ║ $s3[19]=[{:08X}] ║ $k1[27]=[{:08X}] ║'.format(REGS[3], REGS[11], REGS[19], REGS[27]))
#     print('║ $a0[ 4]=[{:08X}] ║ $t4[12]=[{:08X}] ║ $s4[20]=[{:08X}] ║ $gp[28]=[{:08X}] ║'.format(REGS[4], REGS[12], REGS[20], REGS[28]))
#     print('║ $a1[ 5]=[{:08X}] ║ $t5[13]=[{:08X}] ║ $s5[21]=[{:08X}] ║ $sp[29]=[{:08X}] ║'.format(REGS[5], REGS[13], REGS[21], REGS[29]))
#     print('║ $a2[ 6]=[{:08X}] ║ $t6[14]=[{:08X}] ║ $s6[22]=[{:08X}] ║ $fp[30]=[{:08X}] ║'.format(REGS[6], REGS[14], REGS[22], REGS[30]))
#     print('║ $a3[ 7]=[{:08X}] ║ $t7[15]=[{:08X}] ║ $s7[23]=[{:08X}] ║ $ra[31]=[{:08X}] ║'.format(REGS[7], REGS[15], REGS[23], REGS[31]))
#     print('╚════════════════════╩════════════════════╩════════════════════╩════════════════════╝')

# def printDataMem():
#     print('    ╔══════════════════╦═══════════════[MEMORY]══════════════╦══════════════════╗')

#     memSize = len(DATA)
#     for i in range(memSize//4):
#         a, b, c, d = i*4, (memSize)+i*4, (memSize*2)+i*4, (memSize*3)+i*4
#         print('    ║ [{:03}]=[{:08X}] ║ [{:03}]=[{:08X}] ║ [{:03}]=[{:08X}] ║ [{:03}]=[{:08X}] ║'.format(a, DATA[a//4], b, DATA[b//4], c, DATA[c//4], d, DATA[d//4]))        

#     print('    ╚══════════════════╩══════════════════╩══════════════════╩══════════════════╝')

def printHistory(clkHistory):
    # Convert clkHistory to history board
    history = [[' ' for i in range(len(clkHistory))] for i in range(len(INST))]
    for i in range(len(clkHistory)):
        for exe in clkHistory[i]:
            if exe[2]: # Idle
                history[exe[1][0]][i] = ' '
                # history[exe[1][0]][i] = '(' + exe[0] + ')' # Show idle stages
            else:
                history[exe[1][0]][i] = exe[0]

    # Print header and column titles
    print('╔═════╦════════════════════════╦' + '═'*(6*len(clkHistory)) + '╗')
    print('║ Mem ║ ' + 'Clock #'.center(22) + ' ║', end='')
    for i in range(len(clkHistory)):
        print(str(i).center(5), end=' ')
    print('║')
    print('╠═════╬════════════════════════╬' + '═'*(6*len(clkHistory)) + '╣')

    # Print history board
    for i in range(len(history)):
        print('║ {:>3} ║ {:>22} ║'.format(i*4, decode(INST[i])), end='')
        for j in range(len(history[0])):
            print(history[i][j].center(5), end=' ')
        print('║')
    print('╚═════╩════════════════════════╩' + '═'*(6*len(clkHistory)) + '╝')



#############################################################################
# main.py down
#############################################################################

import sys
#import instTranslator
#import stages
#import utils

#import G_MEM, G_UTL

def main():
    try:
        filename = next(arg for arg in sys.argv[1:] if not arg.startswith('-'))
    except StopIteration:
        filename = 'program.asm'

    # Read .asm
    program = readFile(filename)
    programLength = len(program)

    # Encode and load .asm into memory
    for i in range(programLength):
        # Remove comments
        if not program[i] or program[i][0] == '#': continue
        encoded = encode(program[i].split('#')[0])

        # Detect errors, if none then continue loading
        if encoded not in ERROR:
            INST.append(encoded)
        else:
            print(f'ERROR @ \'{filename}\':')
            print(f'\tLine {i+1}: \'{program[i]}\'')
            if encoded == EINST:
                print('\t\tCouldn\'t parse the instruction')
            elif encoded == EARG:
                print('\t\tCouldn\'t parse one or more arguments')
            elif encoded == EFLOW:
                print('\t\tOne or more arguments are under/overflowing')
            return

    # Print the program as loaded
    #clearprintInstMem()
    print()

    # Doesn't print memory after each clock
    silent = ('-s' in sys.argv)

    # Skips clock stepping
    skipSteps = silent

    # Run simulation, will run until all pipeline stages are empty
    clkHistory = []
    clk = 0
    while clk == 0 or (ran['IF'][1] != 0 or ran['ID'][1] != 0 or ran['EX'][1] != 0 or ran['MEM'][1] != 0):
        # if silent:
        #     print(' '.join(['─'*20, f'CLK #{clk}', '─'*20]))
        # else:
        #     print(' '.join(['─'*38, f'CLK #{clk}', '─'*38]))

        clkHistory.append([])

        # Run all stages 'in parallel'
        EX_fwd()
        WB()
        MEM()
        EX()
        ID()
        IF()
        ID_hzd()

        # Keep only the 32 LSB from memory
        for i in range(len(REGS)):
            REGS[i] &= 0xFFFFFFFF
        for i in range(len(DATA)):
            DATA[i] &= 0xFFFFFFFF

        # Report if stage was run
        for stage in ['IF', 'ID', 'EX', 'MEM', 'WB']:
            if ran[stage][1] != 0:
                idle = ' (idle)' if wasIdle[stage] else ''
                clkHistory[clk].append((stage, ran[stage], wasIdle[stage]))
                # print(f'> Stage {stage}: #{ran[stage][0]*4} = [{decode(ran[stage][1])}]{idle}.')

        # Print resulting memory
        # if not silent:
        #     print('─'*(83+len(str(clk))))
        #     # printPC()
        #     # if data_hzd or ctrl_hzd:
        #     #     printFwdAndHazard()
        #     # printPipelineRegs()
        #     # printRegMem()
        #     # printDataMem()
        #     print('─'*(83+len(str(clk))))
        clk += 1

        # Clock step prompt
        # if not skipSteps:
        #     try:
        #         opt = input('| step: [ENTER] | end: [E|Q] | ').lower()
        #         skipSteps = (opt == 'e' or opt == 'q')
        #     except KeyboardInterrupt:
        #         print('\nExecution aborted.')
        #         exit()

    # if silent:
    #     print()
    #     # printPipelineRegs()
    #     # printRegMem()
    #     # printDataMem()
    # else:
    # print('Empty pipeline, ending execution...')

    print()
    print(f'Program ran in {clk} clocks.')
    print()

    printHistory(clkHistory)

    return

if __name__ == '__main__':
    # To print (pipe to file) pretty borders on Windows
    if sys.platform == 'win32': 
        sys.stdout.reconfigure(encoding='UTF-8')

    main()