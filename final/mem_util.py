#flags to track the instructions execution
run_flag = {'IF': (0, 0), 'ID': (0, 0), 'EX': (0, 0), 'MEM': (0, 0), 'WB': (0, 0)}
idleOrNot = {'IF': False, 'ID': False, 'EX': False, 'MEM': False, 'WB': False}

# Dictionaries for easier processing
R_inst = { 'add': 0b100000, 'sub': 0b100010, 'and': 0b100100,  'or': 0b100101,
           'sll': 0b000000, 'srl': 0b000010, 'xor': 0b100110, 'nor': 0b100111,
           'mult': 0b011000, 'div': 0b011001}

RegistersALL = ['$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3',
              '$t0', '$t1', '$t2', '$t3', '$t4', '$t5', '$t6', '$t7',
              '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
              '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra']


MemorySize = 64

instERROR = -1
argumentERROR = -2
overinflowERROR = -3
allERRORS = [instERROR, argumentERROR, overinflowERROR]

DHZD_flag = True

#helper variables
outFWD_A = 0
outFWD_B = 0

# Program Counter
PC = 0

# Instruction Memory
Imem = []

# Registers
reg = [0 for i in range(32)]

# Data Memory
Dmem = [0 for i in range(MemorySize)]

# Pipeline Registers
pipeRegIF_ID = {'pc_Val': 0, 'instReg': 0}
pipeRegID_EX = {'pc_Val': 0, 'valA': 0, 'valB': 0, 'rt': 0, 'rd': 0, 'imm': 0, 'rs': 0}
pipeRegEX_MEM = {'ZERO': 0, 'outALU': 0, 'valB': 0, 'rd': 0}
pipeRegMEM_WB = {'LMD': 0, 'outALU': 0, 'rd': 0}

# Control Signals
ctrlID_EX = {'reg_dst': 0, 'alu_src': 0, 'mem_to_reg': 0, 'reg_write': 0, 'mem_read': 0, 'mem_write': 0, 'alu_OP': 0}
ctrlEX_MEM = {'mem_read': 0, 'mem_write': 0, 'mem_to_reg': 0, 'reg_write': 0}
ctrlMEM_WB = {'mem_to_reg': 0, 'reg_write': 0}

# Forwarding Unit Signals
otherSignals = {'pcWrite': 1, 'IF_ID_write': 1, 'Afwd': 0, 'Bfwd': 0, 'stall': 0}

# Control Unit ROM
#   RegDst, ALUSrc, MemToReg, RegWrite, MemRead, MemWrite, AluOp
ControlSignals = {0b000000: (0b1, 0b0, 0b0, 0b1, 0b0, 0b0, 0b10),  # R-Type
                  0b100011: (0b0, 0b1, 0b1, 0b1, 0b1, 0b0, 0b00),  # lw
                  0b101011: (0b0, 0b1, 0b0, 0b0, 0b0, 0b1, 0b00),  # sw
                  0b001000: (0b0, 0b1, 0b0, 0b1, 0b0, 0b0, 0b00)}  # addi

# encoding the instructions from string to int
def translate(instruction):
    instruction = instruction.replace(',', '')

    # Replace register names with its index
    for i in range(len(RegistersALL)):
        instruction = instruction.replace(RegistersALL[i], str(i))
    instruction = instruction.replace('$', '')

    instruction = instruction.split()

    out = instERROR
    if instruction[0] in R_inst: # R-Type
        out = 0

        if instruction[0] == 'sll' or instruction[0] == 'srl':
            try:
                rd, rt, shamt = [int(i, 0) for i in instruction[1:]] # Accepts any base (e.g. 0b, 0o, 0x)
                
            except:
                return argumentERROR # Not correct number of arguments

            # Check for under/overflow
            nrd, nrt, nshamt = rd&0x1F, rt&0x1F, shamt&0x1F
            if [nrd, nrt, nshamt] != [rd, rt, shamt]:
                return overinflowERROR
            rd, rt, shamt = nrd, nrt, nshamt

            # Encode
            out |= rt
            out <<= 5
            out |= rd
            out <<= 5
            out |= shamt
            out <<= 6
            out |= R_inst[instruction[0]]

        else: # R-Types other than sll/srl
            try:
                rd, rs, rt = [int(i, 0) for i in instruction[1:]] # Accepts any base (e.g. 0b, 0o, 0x)
            except:
                return argumentERROR # Not correct number of arguments

            # Check for under/overflow
            nrd, nrs, nrt = rd&0x1F, rs&0x1F, rt&0x1F
            if [nrd, nrs, nrt] != [rd, rs, rt]:
                return overinflowERROR
            rd, rs, rt = nrd, nrs, nrt

            # Encode
            out |= rs
            out <<= 5
            out |= rt
            out <<= 5
            out |= rd
            out <<= 11
            out |= R_inst[instruction[0]]

    elif instruction[0] == 'lw' or instruction[0] == 'sw':
        opcode = {'lw': 0b100011, 'sw': 0b101011}
        out = opcode[instruction[0]] << 5

        try:
            instruction[2] = instruction[2].split('(')
            instruction[2:] = instruction[2][0], instruction[2][1][:-1]

            rt, offset, rs = [int(i, 0) for i in instruction[1:]]
        except:
            return argumentERROR # Not correct number of arguments

        # Check for under/overflow
        nrt, nrs, noffset = rt&0x1F, rs&0x1F, offset&0xFFFF
        if [nrt, nrs, noffset] != [rt, rs, offset]:
            return overinflowERROR
        rt, rs, offset = nrt, nrs, noffset

        # Encode
        out |= rs
        out <<= 5
        out |= rt
        out <<= 16
        out |= offset

    elif instruction[0] == 'addi':
        out = 0b001000 << 5

        try:
            rt, rs, imm = [int(i, 0) for i in instruction[1:]]
        except:
            return argumentERROR

        # Check for under/overflow
        nrt, nrs, nimm = rt&0x1F, rs&0x1F, imm&0xFFFF
        if [nrt, nrs, nimm] != [rt, rs, imm]:
            return overinflowERROR
        rt, rs, imm = nrt, nrs, nimm

        # Encode
        out |= rs
        out <<= 5
        out |= rt
        out <<= 16
        out |= imm

    return out

    
