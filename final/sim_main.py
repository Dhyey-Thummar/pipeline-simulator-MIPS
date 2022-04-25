import sys
import mem_util as memory
import mem_util as util
import sim_stages as stg

def main():
    try:
        filename = next(arg for arg in sys.argv[1:] if not arg.startswith('-'))
    except StopIteration:
        filename = 'program.asm'

    # Read .asm
    program = util.readFile(filename)
    programLength = len(program)

    # Encode and load .asm into memory
    for i in range(programLength):
        # Remove comments
        if not program[i] or program[i][0] == '#': continue
        encoded = util.encode(program[i].split('#')[0])

        # Detect errors, if none then continue loading
        if encoded not in util.ERROR:
            memory.INST.append(encoded)
        else:
            print(f'ERROR @ \'{filename}\':')
            print(f'\tLine {i+1}: \'{program[i]}\'')
            if encoded == util.EINST:
                print('\t\tCouldn\'t parse the instruction')
            elif encoded == util.EARG:
                print('\t\tCouldn\'t parse one or more arguments')
            elif encoded == util.EFLOW:
                print('\t\tOne or more arguments are under/overflowing')
            return

    # Print the program as loaded

    print()

    # Run simulation, will run until all pipeline stages are empty
    clkHistory = []
    clk = 0
    while clk == 0 or (util.ran['IF'][1] != 0 or util.ran['ID'][1] != 0 or util.ran['EX'][1] != 0 or util.ran['MEM'][1] != 0):
        
        clkHistory.append([])

        # Run all stages 'in parallel'
        stg.EX_fwd()
        stg.WB()
        stg.MEM()
        stg.EX()
        stg.ID()
        stg.IF()
        stg.ID_hzd()

        # Keep only the 32 LSB from memory
        for i in range(len(memory.REGS)):
            memory.REGS[i] &= 0xFFFFFFFF
        for i in range(len(memory.DATA)):
            memory.DATA[i] &= 0xFFFFFFFF

        # Report if stage was run
        for stage in ['IF', 'ID', 'EX', 'MEM', 'WB']:
            if util.ran[stage][1] != 0:
                idle = ' (idle)' if util.wasIdle[stage] else ''
                clkHistory[clk].append((stage, util.ran[stage], util.wasIdle[stage]))

        clk += 1

    print()
    print(f'Program ran in {clk} clocks.')
    print()

    util.printHistory(clkHistory)

    return

if __name__ == '__main__':
    # To print (pipe to file) pretty borders on Windows
    if sys.platform == 'win32': 
        sys.stdout.reconfigure(encoding='UTF-8')

    main()