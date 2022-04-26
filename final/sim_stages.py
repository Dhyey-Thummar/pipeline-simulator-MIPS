import mem_util as memory
import mem_util as util

def DoForwarding():
    # Forwarding Unit
    if memory.ctrlMEM_WB['reg_write'] == 1 and memory.pipeRegMEM_WB['rd'] != 0 and memory.pipeRegMEM_WB['rd'] == memory.pipeRegID_EX['rs'] and (memory.pipeRegEX_MEM['rd'] != memory.pipeRegID_EX['rs'] or memory.ctrlEX_MEM['reg_write'] == 0):
        memory.otherSignals['Afwd'] = 1
    elif memory.ctrlEX_MEM['reg_write'] == 1 and memory.pipeRegEX_MEM['rd'] != 0 and memory.pipeRegEX_MEM['rd'] == memory.pipeRegID_EX['rs']:
        memory.otherSignals['Afwd'] = 2
    else:
        memory.otherSignals['Afwd'] = 0

    if memory.ctrlMEM_WB['reg_write'] == 1 and memory.pipeRegMEM_WB['rd'] != 0 and memory.pipeRegMEM_WB['rd'] == memory.pipeRegID_EX['rt'] and (memory.pipeRegEX_MEM['rd'] != memory.pipeRegID_EX['rt'] or memory.ctrlEX_MEM['reg_write'] == 0):
        memory.otherSignals['Bfwd'] = 1
    elif memory.ctrlEX_MEM['reg_write'] == 1 and memory.pipeRegEX_MEM['rd'] != 0 and memory.pipeRegEX_MEM['rd'] == memory.pipeRegID_EX['rt']:
        memory.otherSignals['Bfwd'] = 2
    else:
        memory.otherSignals['Bfwd'] = 0

    # FwdA Multiplexer
    if memory.otherSignals['Afwd'] == 0 or not util.DHZD_flag:
        util.outFWD_A = memory.pipeRegID_EX['valA']
    elif memory.otherSignals['Afwd'] == 1:
        if memory.ctrlMEM_WB['mem_to_reg'] == 1:
            util.outFWD_A = memory.pipeRegMEM_WB['LMD']
        else:
            util.outFWD_A = memory.pipeRegMEM_WB['outALU']
    elif memory.otherSignals['Afwd'] == 2:
        util.outFWD_A = memory.pipeRegEX_MEM['outALU']

    # FwdB Multiplexer
    if memory.otherSignals['Bfwd'] == 0 or not util.DHZD_flag:
        util.outFWD_B = memory.pipeRegID_EX['valB']
    elif memory.otherSignals['Bfwd'] == 1:
        # MemToReg Multiplexer
        if memory.ctrlMEM_WB['mem_to_reg'] == 1:
            util.outFWD_B = memory.pipeRegMEM_WB['LMD']
        else:
            util.outFWD_B = memory.pipeRegMEM_WB['outALU']
    elif memory.otherSignals['Bfwd'] == 2:
        util.outFWD_B = memory.pipeRegEX_MEM['outALU']

def HazardCheck():
    # Hazard Unit
    if_id_rs = (memory.pipeRegIF_ID['instReg'] & 0x03E00000) >> 21 # instReg[25..21]
    if_id_rt = (memory.pipeRegIF_ID['instReg'] & 0x001F0000) >> 16 # instReg[20..16]

    if memory.ctrlID_EX['mem_read'] == 1 and (memory.pipeRegID_EX['rt'] == if_id_rs or memory.pipeRegID_EX['rt'] == if_id_rt) and util.DHZD_flag:
        memory.otherSignals['pcWrite'] = 0
        memory.otherSignals['IF_ID_write'] = 0
        memory.otherSignals['stall'] = 1
    else:
        memory.otherSignals['pcWrite'] = 1
        memory.otherSignals['IF_ID_write'] = 1
        memory.otherSignals['stall'] = 0

def InstFetch():
    # Grab instruction from memory array
    try:
        curInst = memory.Imem[memory.PC//4]
    except IndexError:
        curInst = 0

    # Set simulator flags
    util.run_flag['IF'] = (0, 0) if memory.otherSignals['stall'] == 1 else (memory.PC//4, curInst)
    util.idleOrNot['IF'] = (memory.otherSignals['stall'] == 1)

    if memory.otherSignals['IF_ID_write'] == 1 or not util.DHZD_flag:
        # Set IF/ID.pc_Val
        memory.pipeRegIF_ID['pc_Val'] = memory.PC + 4

        # Set IF/ID.instReg
        memory.pipeRegIF_ID['instReg'] = curInst

    if memory.otherSignals['pcWrite'] == 1 or not util.DHZD_flag:
        if memory.otherSignals['stall'] != 1:
            memory.PC = memory.PC + 4

def InstDecode():
    # Set simulator flags
    util.run_flag['ID'] = (0, 0) if memory.otherSignals['stall'] == 1 else util.run_flag['IF']
    util.idleOrNot['ID'] = (memory.otherSignals['stall'] == 1)

    if memory.otherSignals['stall'] == 1:
        # Stall the pipeline, adding a bubble
        memory.ctrlID_EX['reg_dst'] = 0
        memory.ctrlID_EX['alu_src'] = 0
        memory.ctrlID_EX['mem_to_reg'] = 0
        memory.ctrlID_EX['reg_write'] = 0
        memory.ctrlID_EX['mem_read'] = 0
        memory.ctrlID_EX['mem_write'] = 0
        memory.ctrlID_EX['alu_OP'] = 0
    else:
        # Set Control of ID/EX (Control Unit)
        opcode = (memory.pipeRegIF_ID['instReg'] & 0xFC000000) >> 26 # instReg[31..26]
        
        memory.ctrlID_EX['reg_dst'] = util.ControlSignals[opcode][0]
        memory.ctrlID_EX['alu_src'] = util.ControlSignals[opcode][1]
        memory.ctrlID_EX['mem_to_reg'] = util.ControlSignals[opcode][2]
        memory.ctrlID_EX['reg_write'] = util.ControlSignals[opcode][3]
        memory.ctrlID_EX['mem_read'] = util.ControlSignals[opcode][4]
        memory.ctrlID_EX['mem_write'] = util.ControlSignals[opcode][5]
        memory.ctrlID_EX['alu_OP'] = util.ControlSignals[opcode][6]

    # Set ID/EX.pc_Val
    memory.pipeRegID_EX['pc_Val'] = memory.pipeRegIF_ID['pc_Val']

    # Set ID/EX.valA
    reg1 = (memory.pipeRegIF_ID['instReg'] & 0x03E00000) >> 21 # instReg[25..21]
    memory.pipeRegID_EX['valA'] = memory.reg[reg1]

    # Set ID/EX.valB
    reg2 = (memory.pipeRegIF_ID['instReg'] & 0x001F0000) >> 16 # instReg[20..16]
    memory.pipeRegID_EX['valB'] = memory.reg[reg2]

    # Set ID/EX.rt
    memory.pipeRegID_EX['rt'] = (memory.pipeRegIF_ID['instReg'] & 0x001F0000) >> 16 # instReg[20..16]

    # Set ID/EX.rd
    memory.pipeRegID_EX['rd'] = (memory.pipeRegIF_ID['instReg'] & 0x0000F800) >> 11 # instReg[15..11]

    # Set ID/EX.Imm (Sign Extend)
    imm = (memory.pipeRegIF_ID['instReg'] & 0x0000FFFF) >> 0 # instReg[15..0]
    memory.pipeRegID_EX['imm'] = imm

    # Set ID/EX.rs
    memory.pipeRegID_EX['rs'] = (memory.pipeRegIF_ID['instReg'] & 0x03E00000) >> 21 # instReg[25..21]
    

def Execute():
    # Set simulator flags
    util.run_flag['EX'] = util.run_flag['ID']
    util.idleOrNot['EX'] = False

    # Set Control of EX/MEM based on Control of ID/EX
    memory.ctrlEX_MEM['mem_to_reg'] = memory.ctrlID_EX['mem_to_reg']
    memory.ctrlEX_MEM['reg_write'] = memory.ctrlID_EX['reg_write']
    memory.ctrlEX_MEM['mem_read'] = memory.ctrlID_EX['mem_read']
    memory.ctrlEX_MEM['mem_write'] = memory.ctrlID_EX['mem_write']

    # Set internal ALU source valA
    a = util.outFWD_A

    # Set internal ALU source valB (valB Multiplexer)
    if memory.ctrlID_EX['alu_src'] == 1:
        b = memory.pipeRegID_EX['imm']
    else:
        b = util.outFWD_B

    # Set EX/MEM.Zero (ALU)
    if a - b == 0:
        memory.pipeRegEX_MEM['ZERO'] = 1
    else:
        memory.pipeRegEX_MEM['ZERO'] = 0

    # Set EX/MEM.AluOut (ALU + ALU Control)
    out = 0
    if memory.ctrlID_EX['alu_OP'] == 0: # Add (lw/sw/addi)
        out = a + b
    elif memory.ctrlID_EX['alu_OP'] == 1: # Sub
        out = a - b
    elif memory.ctrlID_EX['alu_OP'] == 2: # R-Type
        funct = memory.pipeRegID_EX['imm'] & 0x0000003F # instReg[5..0]
        shamt = memory.pipeRegID_EX['imm'] & 0x000007C0 # instReg[10..6]
        if funct == util.R_inst['add']:
            out = a + b
        elif funct == util.R_inst['sub']:
            out = a - b
        elif funct == util.R_inst['and']:
            out = a & b
        elif funct == util.R_inst['or']:
            out = a | b
        elif funct == util.R_inst['sll']:
            out = a << shamt
        elif funct == util.R_inst['srl']:
            out = a >> shamt
        elif funct == util.R_inst['xor']:
            out = a ^ b
        elif funct == util.R_inst['nor']:
            out = ~(a | b)
        elif funct == util.R_inst['mult']:
            out = a * b
        elif funct == util.R_inst['div']:
            out = a // b
    memory.pipeRegEX_MEM['outALU'] = out

    # Set EX/MEM.valB
    memory.pipeRegEX_MEM['valB'] = util.outFWD_B

    # Set EX/MEM.rd (RegDst Multiplexer)
    if memory.ctrlID_EX['reg_dst'] == 1:
        memory.pipeRegEX_MEM['rd'] = memory.pipeRegID_EX['rd']
    else:
        memory.pipeRegEX_MEM['rd'] = memory.pipeRegID_EX['rt']

def MemoryAccess():
    # Set simulator flags
    util.run_flag['MEM'] = util.run_flag['EX']
    util.idleOrNot['MEM'] = memory.ctrlEX_MEM['mem_read'] != 1 and memory.ctrlEX_MEM['mem_write'] != 1

    # Set Control of MEM/WB based on Control of EX/MEM
    memory.ctrlMEM_WB['mem_to_reg'] = memory.ctrlEX_MEM['mem_to_reg']
    memory.ctrlMEM_WB['reg_write'] = memory.ctrlEX_MEM['reg_write']

    # Set MEM/WB.LMD (read from Data Memory)
    if memory.ctrlEX_MEM['mem_read'] == 1:
        # The simulation memory might not be big enough
        if memory.pipeRegEX_MEM['outALU']//4 < util.MemorySize:
            memory.pipeRegMEM_WB['LMD'] = memory.Dmem[memory.pipeRegEX_MEM['outALU']//4]
        else:
            print('***WARNING***')
            print(f'\tMemory Read at position {memory.pipeRegEX_MEM["outALU"]} not executed:')
            print(f'\t\tMemory only has {util.MemorySize*4} positions.')
            
            try:
                input('Press ENTER to continue execution or abort with CTRL-C. ')
            except KeyboardInterrupt:
                print('Execution aborted.')
                exit()
    
    # Write to Data Memory
    if memory.ctrlEX_MEM['mem_write'] == 1:
        # The simulation memory might not be big enough
        if memory.pipeRegEX_MEM['outALU']//4 < util.MemorySize:
            memory.Dmem[memory.pipeRegEX_MEM['outALU']//4] = memory.pipeRegEX_MEM['valB']
        else:
            print('***WARNING***')
            print(f'\tMemory Write at position {memory.pipeRegEX_MEM["outALU"]} not executed:')
            print(f'\t\tMemory only has {util.MemorySize*4} positions.')
            exit()
    
    # Set MEM/WB.ALUOut
    memory.pipeRegMEM_WB['outALU'] = memory.pipeRegEX_MEM['outALU']

    # Set MEM/WB.rd
    memory.pipeRegMEM_WB['rd'] = memory.pipeRegEX_MEM['rd']

def WriteBack():
    # Set simulator flags
    util.run_flag['WB'] = util.run_flag['MEM']
    util.idleOrNot['WB'] = memory.ctrlMEM_WB['reg_write'] != 1 or memory.pipeRegMEM_WB['rd'] == 0

    # Write to Registers
    if memory.ctrlMEM_WB['reg_write'] == 1 and memory.pipeRegMEM_WB['rd'] != 0:
        # MemToReg Multiplexer
        if memory.ctrlMEM_WB['mem_to_reg'] == 1:
            memory.reg[memory.pipeRegMEM_WB['rd']] = memory.pipeRegMEM_WB['LMD']
        else:
            memory.reg[memory.pipeRegMEM_WB['rd']] = memory.pipeRegMEM_WB['outALU']