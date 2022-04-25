import mem_util as memory
import mem_util as util

# Control Unit ROM
# RegDst, ALUSrc, MemToReg, RegWrite, MemRead, MemWrite, Branch, AluOp
ctrl = {0b000000: (0b1, 0b0, 0b0, 0b1, 0b0, 0b0, 0b0, 0b10), # R-Type
        0b100011: (0b0, 0b1, 0b1, 0b1, 0b1, 0b0, 0b0, 0b00), # lw
        0b101011: (0b0, 0b1, 0b0, 0b0, 0b0, 0b1, 0b0, 0b00), # sw
        0b000100: (0b0, 0b0, 0b0, 0b0, 0b0, 0b0, 0b1, 0b01), # beq
        0b001000: (0b0, 0b1, 0b0, 0b1, 0b0, 0b0, 0b0, 0b00)} # addi

def EX_fwd():
    # Forwarding Unit
    if memory.MEM_WB_CTRL['REG_WRITE'] == 1 and memory.MEM_WB['RD'] != 0 and memory.MEM_WB['RD'] == memory.ID_EX['RS'] and (memory.EX_MEM['RD'] != memory.ID_EX['RS'] or memory.EX_MEM_CTRL['REG_WRITE'] == 0):
        memory.FWD['FWD_A'] = 1
    elif memory.EX_MEM_CTRL['REG_WRITE'] == 1 and memory.EX_MEM['RD'] != 0 and memory.EX_MEM['RD'] == memory.ID_EX['RS']:
        memory.FWD['FWD_A'] = 2
    else:
        memory.FWD['FWD_A'] = 0

    if memory.MEM_WB_CTRL['REG_WRITE'] == 1 and memory.MEM_WB['RD'] != 0 and memory.MEM_WB['RD'] == memory.ID_EX['RT'] and (memory.EX_MEM['RD'] != memory.ID_EX['RT'] or memory.EX_MEM_CTRL['REG_WRITE'] == 0):
        memory.FWD['FWD_B'] = 1
    elif memory.EX_MEM_CTRL['REG_WRITE'] == 1 and memory.EX_MEM['RD'] != 0 and memory.EX_MEM['RD'] == memory.ID_EX['RT']:
        memory.FWD['FWD_B'] = 2
    else:
        memory.FWD['FWD_B'] = 0

    # FwdA Multiplexer
    if memory.FWD['FWD_A'] == 0 or not util.data_hzd:
        util.outFwdA = memory.ID_EX['A']
    elif memory.FWD['FWD_A'] == 1:
        if memory.MEM_WB_CTRL['MEM_TO_REG'] == 1:
            util.outFwdA = memory.MEM_WB['LMD']
        else:
            util.outFwdA = memory.MEM_WB['ALU_OUT']
    elif memory.FWD['FWD_A'] == 2:
        util.outFwdA = memory.EX_MEM['ALU_OUT']

    # FwdB Multiplexer
    if memory.FWD['FWD_B'] == 0 or not util.data_hzd:
        util.outFwdB = memory.ID_EX['B']
    elif memory.FWD['FWD_B'] == 1:
        # MemToReg Multiplexer
        if memory.MEM_WB_CTRL['MEM_TO_REG'] == 1:
            util.outFwdB = memory.MEM_WB['LMD']
        else:
            util.outFwdB = memory.MEM_WB['ALU_OUT']
    elif memory.FWD['FWD_B'] == 2:
        util.outFwdB = memory.EX_MEM['ALU_OUT']

def ID_hzd():
    # Hazard Unit
    if_id_rs = (memory.IF_ID['IR'] & 0x03E00000) >> 21 # IR[25..21]
    if_id_rt = (memory.IF_ID['IR'] & 0x001F0000) >> 16 # IR[20..16]

    if memory.ID_EX_CTRL['MEM_READ'] == 1 and (memory.ID_EX['RT'] == if_id_rs or memory.ID_EX['RT'] == if_id_rt) and util.data_hzd:
        memory.FWD['PC_WRITE'] = 0
        memory.FWD['IF_ID_WRITE'] = 0
        memory.FWD['STALL'] = 1
    elif (memory.ID_EX_CTRL['BRANCH'] == 1 or memory.EX_MEM_CTRL['BRANCH'] == 1) and util.ctrl_hzd:
        memory.FWD['IF_ID_WRITE'] = 0
        memory.FWD['STALL'] = 1
    else:
        memory.FWD['PC_WRITE'] = 1
        memory.FWD['IF_ID_WRITE'] = 1
        memory.FWD['STALL'] = 0

def IF():
    # Grab instruction from memory array
    try:
        curInst = memory.INST[memory.PC//4]
    except IndexError:
        curInst = 0

    # Set simulator flags
    util.ran['IF'] = (0, 0) if memory.FWD['STALL'] == 1 else (memory.PC//4, curInst)
    util.wasIdle['IF'] = (memory.FWD['STALL'] == 1)

    if memory.FWD['IF_ID_WRITE'] == 1 or not util.data_hzd:
        # Set IF/ID.NPC
        memory.IF_ID['NPC'] = memory.PC + 4

        # Set IF/ID.IR
        memory.IF_ID['IR'] = curInst

    if memory.FWD['PC_WRITE'] == 1 or not util.data_hzd:
        # Set own PC (PC Multiplexer)
        if memory.EX_MEM['ZERO'] == 1 and memory.EX_MEM_CTRL['BRANCH'] == 1:
            memory.PC = memory.EX_MEM['BR_TGT']
        elif memory.FWD['STALL'] != 1:
            memory.PC = memory.PC + 4

def ID():
    # Set simulator flags
    util.ran['ID'] = (0, 0) if memory.FWD['STALL'] == 1 else util.ran['IF']
    util.wasIdle['ID'] = (memory.FWD['STALL'] == 1)

    if memory.FWD['STALL'] == 1:
        # Stall the pipeline, adding a bubble
        memory.ID_EX_CTRL['REG_DST'] = 0
        memory.ID_EX_CTRL['ALU_SRC'] = 0
        memory.ID_EX_CTRL['MEM_TO_REG'] = 0
        memory.ID_EX_CTRL['REG_WRITE'] = 0
        memory.ID_EX_CTRL['MEM_READ'] = 0
        memory.ID_EX_CTRL['MEM_WRITE'] = 0
        memory.ID_EX_CTRL['BRANCH'] = 0
        memory.ID_EX_CTRL['ALU_OP'] = 0
    else:
        # Set Control of ID/EX (Control Unit)
        opcode = (memory.IF_ID['IR'] & 0xFC000000) >> 26 # IR[31..26]
        memory.ID_EX_CTRL['REG_DST'] = ctrl[opcode][0]
        memory.ID_EX_CTRL['ALU_SRC'] = ctrl[opcode][1]
        memory.ID_EX_CTRL['MEM_TO_REG'] = ctrl[opcode][2]
        memory.ID_EX_CTRL['REG_WRITE'] = ctrl[opcode][3]
        memory.ID_EX_CTRL['MEM_READ'] = ctrl[opcode][4]
        memory.ID_EX_CTRL['MEM_WRITE'] = ctrl[opcode][5]
        memory.ID_EX_CTRL['BRANCH'] = ctrl[opcode][6]
        memory.ID_EX_CTRL['ALU_OP'] = ctrl[opcode][7]

    # Set ID/EX.NPC
    memory.ID_EX['NPC'] = memory.IF_ID['NPC']

    # Set ID/EX.A
    reg1 = (memory.IF_ID['IR'] & 0x03E00000) >> 21 # IR[25..21]
    memory.ID_EX['A'] = memory.REGS[reg1]

    # Set ID/EX.B
    reg2 = (memory.IF_ID['IR'] & 0x001F0000) >> 16 # IR[20..16]
    memory.ID_EX['B'] = memory.REGS[reg2]

    # Set ID/EX.RT
    memory.ID_EX['RT'] = (memory.IF_ID['IR'] & 0x001F0000) >> 16 # IR[20..16]

    # Set ID/EX.RD
    memory.ID_EX['RD'] = (memory.IF_ID['IR'] & 0x0000F800) >> 11 # IR[15..11]

    # Set ID/EX.Imm (Sign Extend)
    imm = (memory.IF_ID['IR'] & 0x0000FFFF) >> 0 # IR[15..0]
    memory.ID_EX['IMM'] = imm

    # Set ID/EX.RS
    memory.ID_EX['RS'] = (memory.IF_ID['IR'] & 0x03E00000) >> 21 # IR[25..21]

def EX():
    # Set simulator flags
    util.ran['EX'] = util.ran['ID']
    util.wasIdle['EX'] = False

    # Set Control of EX/MEM based on Control of ID/EX
    memory.EX_MEM_CTRL['MEM_TO_REG'] = memory.ID_EX_CTRL['MEM_TO_REG']
    memory.EX_MEM_CTRL['REG_WRITE'] = memory.ID_EX_CTRL['REG_WRITE']
    memory.EX_MEM_CTRL['BRANCH'] = memory.ID_EX_CTRL['BRANCH']
    memory.EX_MEM_CTRL['MEM_READ'] = memory.ID_EX_CTRL['MEM_READ']
    memory.EX_MEM_CTRL['MEM_WRITE'] = memory.ID_EX_CTRL['MEM_WRITE']

    # Set EX/MEM.BrTgt (Shift Left 2)
    memory.EX_MEM['BR_TGT'] = memory.ID_EX['NPC'] + (memory.ID_EX['IMM'] << 2)

    # Set internal ALU source A
    aluA = util.outFwdA

    # Set internal ALU source B (B Multiplexer)
    if memory.ID_EX_CTRL['ALU_SRC'] == 1:
        aluB = memory.ID_EX['IMM']
    else:
        aluB = util.outFwdB

    # Set EX/MEM.Zero (ALU)
    if aluA - aluB == 0:
        memory.EX_MEM['ZERO'] = 1
    else:
        memory.EX_MEM['ZERO'] = 0

    # Set EX/MEM.AluOut (ALU + ALU Control)
    out = 0
    if memory.ID_EX_CTRL['ALU_OP'] == 0: # Add (lw/sw/addi)
        out = aluA + aluB
    elif memory.ID_EX_CTRL['ALU_OP'] == 1: # Sub (beq)
        out = aluA - aluB
    elif memory.ID_EX_CTRL['ALU_OP'] == 2: # R-Type
        funct = memory.ID_EX['IMM'] & 0x0000003F # IR[5..0]
        shamt = memory.ID_EX['IMM'] & 0x000007C0 # IR[10..6]
        if funct == util.rTypeWords['add']:
            out = aluA + aluB
        elif funct == util.rTypeWords['sub']:
            out = aluA - aluB
        elif funct == util.rTypeWords['and']:
            out = aluA & aluB
        elif funct == util.rTypeWords['or']:
            out = aluA | aluB
        elif funct == util.rTypeWords['sll']:
            out = aluA << shamt
        elif funct == util.rTypeWords['srl']:
            out = aluA >> shamt
        elif funct == util.rTypeWords['xor']:
            out = aluA ^ aluB
        elif funct == util.rTypeWords['nor']:
            out = ~(aluA | aluB)
        elif funct == util.rTypeWords['mult']:
            out = aluA * aluB
        elif funct == util.rTypeWords['div']:
            out = aluA // aluB
    memory.EX_MEM['ALU_OUT'] = out

    # Set EX/MEM.B
    memory.EX_MEM['B'] = util.outFwdB

    # Set EX/MEM.RD (RegDst Multiplexer)
    if memory.ID_EX_CTRL['REG_DST'] == 1:
        memory.EX_MEM['RD'] = memory.ID_EX['RD']
    else:
        memory.EX_MEM['RD'] = memory.ID_EX['RT']

def MEM():
    # Set simulator flags
    util.ran['MEM'] = util.ran['EX']
    util.wasIdle['MEM'] = memory.EX_MEM_CTRL['MEM_READ'] != 1 and memory.EX_MEM_CTRL['MEM_WRITE'] != 1

    # Set Control of MEM/WB based on Control of EX/MEM
    memory.MEM_WB_CTRL['MEM_TO_REG'] = memory.EX_MEM_CTRL['MEM_TO_REG']
    memory.MEM_WB_CTRL['REG_WRITE'] = memory.EX_MEM_CTRL['REG_WRITE']

    # Set MEM/WB.LMD (read from Data Memory)
    if memory.EX_MEM_CTRL['MEM_READ'] == 1:
        # The simulation memory might not be big enough
        if memory.EX_MEM['ALU_OUT']//4 < util.DATA_SIZE:
            memory.MEM_WB['LMD'] = memory.DATA[memory.EX_MEM['ALU_OUT']//4]
        else:
            print('***WARNING***')
            print(f'\tMemory Read at position {memory.EX_MEM["ALU_OUT"]} not executed:')
            print(f'\t\tMemory only has {util.DATA_SIZE*4} positions.')
            
            try:
                input('Press ENTER to continue execution or abort with CTRL-C. ')
            except KeyboardInterrupt:
                print('Execution aborted.')
                exit()
    
    # Write to Data Memory
    if memory.EX_MEM_CTRL['MEM_WRITE'] == 1:
        # The simulation memory might not be big enough
        if memory.EX_MEM['ALU_OUT']//4 < util.DATA_SIZE:
            memory.DATA[memory.EX_MEM['ALU_OUT']//4] = memory.EX_MEM['B']
        else:
            print('***WARNING***')
            print(f'\tMemory Write at position {memory.EX_MEM["ALU_OUT"]} not executed:')
            print(f'\t\tMemory only has {util.DATA_SIZE*4} positions.')
            
            try:
                input('Press ENTER to continue execution or abort with CTRL-C. ')
            except KeyboardInterrupt:
                print('Execution aborted.')
                exit()
    
    # Set MEM/WB.ALUOut
    memory.MEM_WB['ALU_OUT'] = memory.EX_MEM['ALU_OUT']

    # Set MEM/WB.RD
    memory.MEM_WB['RD'] = memory.EX_MEM['RD']

def WB():
    # Set simulator flags
    util.ran['WB'] = util.ran['MEM']
    util.wasIdle['WB'] = memory.MEM_WB_CTRL['REG_WRITE'] != 1 or memory.MEM_WB['RD'] == 0

    # Write to Registers
    if memory.MEM_WB_CTRL['REG_WRITE'] == 1 and memory.MEM_WB['RD'] != 0:
        # MemToReg Multiplexer
        if memory.MEM_WB_CTRL['MEM_TO_REG'] == 1:
            memory.REGS[memory.MEM_WB['RD']] = memory.MEM_WB['LMD']
        else:
            memory.REGS[memory.MEM_WB['RD']] = memory.MEM_WB['ALU_OUT']