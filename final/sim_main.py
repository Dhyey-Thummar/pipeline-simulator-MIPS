import sys
from tkinter import *
import mem_util as memory
import mem_util as util
import sim_stages as stg


def main():
    root = Tk()
    root.geometry("3000x3000")
    root.title("Simulator")
    inputtxt = Text(root, height=10,
                    width=250,
                    bg="light yellow")
    Output = Text(root, height=30,
                  width=250,
                  bg="light cyan")

    clkHistory2 = []

    def Takein():
        INPUT = inputtxt.get(1.0, END)
        program = [i.strip() for i in INPUT.splitlines()]
        programLength = len(program)
        # Encode and load .asm into memory
        for i in range(programLength):
            # Remove comments
            if not program[i] or program[i][0] == '#':
                continue
            encoded = util.encode(program[i].split('#')[0])
            # get the encoded form of the instruction from the
            # Detect errors, if none then continue loading
            if encoded not in util.ERROR:
                memory.INST.append(encoded)
            else:
                # print(f'ERROR @ \'{filename}\':')
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
                    clkHistory[clk].append(
                        (stage, util.ran[stage], util.wasIdle[stage]))

            clk += 1


        print()
        print(f'Program ran in {clk} clocks.')
        print()

        for i in range(len(clkHistory)):
            clkHistory2.append(clkHistory[i])

        util.printHistory(clkHistory)



    def Giveout():
        history = [[' ' for i in range(len(clkHistory2))]
                   for i in range(len(memory.INST))]
        for i in range(len(clkHistory2)):
            for exe in clkHistory2[i]:
                if exe[2]:  # Idle
                    history[exe[1][0]][i] = ' '

                else:
                    history[exe[1][0]][i] = exe[0]

        Output.insert(END, '╔' + '═'*(6*len(clkHistory2)) + '╗'+'\n')
        Output.insert(END, '║')
        for i in range(1, len(clkHistory2)+1):
            Output.insert(END, str(i).center(5)+' ')
        Output.insert(END, '║'+'\n')
        Output.insert(END, '╠' + '═'*(6*len(clkHistory2)) + '╣'+'\n')

    # Print history board
        for i in range(len(history)):
            Output.insert(END, '║')
            for j in range(len(history[0])):
                Output.insert(END, history[i][j].center(5)+' ')
            Output.insert(END, '║'+'\n')
        Output.insert(END, '╚' + '═'*(6*len(clkHistory2)) + '╝'+'\n')

    Display = Button(root, height=2,width=40,text="press when want to take input",command=lambda: Takein())
    Display1 = Button(root, height=2, width=40, text="press when want see output", command=lambda: Giveout())
    Display.pack()
    inputtxt.pack()
    Display1.pack()
    Output.pack()

    mainloop()


if __name__ == '__main__':
    # To print (pipe to file) pretty borders on Windows
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='UTF-8')

    main()
