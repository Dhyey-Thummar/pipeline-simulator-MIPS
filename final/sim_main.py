import sys
from tkinter import *
import mem_util as memory
import mem_util as util
import sim_stages as stg

global err
err = ""

def main():
    global err
    err = ""
    root = Tk()
    root.geometry("3000x3000")
    root.title("Simulator")
    inputtxt = Text(root, height=15, width=250, bg="light yellow")
    Output = Text(root, height=30,width=250,bg="light cyan")

    clkHistory2 = []

    def Takein():
        
        INPUT = inputtxt.get(1.0, END)
        program = [i.strip() for i in INPUT.splitlines()]
        programLength = len(program)
        # Encode and load .asm into memory
        for i in range(programLength):
            encoded = util.encode(program[i].split('#')[0])
            # get the encoded form of the instruction from the
            # Detect errors, if none then continue loading
            if encoded not in util.ERROR:
                memory.INST.append(encoded)
            else:
                global err
                err = ""
                if encoded == util.EINST:
                    err = program[i]+'\t\tCouldn\'t parse the instruction'
                elif encoded == util.EARG:
                    err = program[i]+'\t\tCouldn\'t parse one or more arguments'
                elif encoded == util.EFLOW:
                    err = program[i]+'\t\tOne or more arguments are under/overflowing'
                
                print(err)
                return

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
                    clkHistory[clk].append(
                        (stage, util.ran[stage], util.wasIdle[stage]))

            clk += 1

        print()
        print(f'Program ran in {clk} clocks.')
        print()
        

        for i in range(len(clkHistory)):
            clkHistory2.append(clkHistory[i])


    def Giveout():
        global err
        if err != "":
            Output.insert(END, err)
            return

        history = [[' ' for i in range(len(clkHistory2))]
                   for i in range(len(memory.INST))]
        for i in range(len(clkHistory2)):
            for exe in clkHistory2[i]:
                if exe[2]:  # Idle
                    # Show idle stages
                    history[exe[1][0]][i] = 'Idle'
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

    def Exit():
        sys.exit()

    Display = Button(root, height=2,width=40,text="Press to take input",command=lambda: Takein())
    Display1 = Button(root, height=2, width=40, text="Press to see output", command=lambda: Giveout())
    Display2 = Button(root, height=2, width=40, text="Exit", command=lambda: Exit())

    Display.pack()
    inputtxt.pack()
    Display1.pack()
    Display2.pack()
    Output.pack()

    mainloop()

if __name__ == '__main__':
    main()
