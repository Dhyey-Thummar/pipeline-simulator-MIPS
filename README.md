# MIPS Pipeline Simulator

This is a pipeline simulator for MIPS. It is written in Python and uses the Tkinter library for the GUI.

## Abstract

Pipelining is  a  technique  that  allows  a  processor  to  execute  multiple  instructions  in  parallel.  This  is  done  by  breaking  the  processor  into  multiple  stages  and  allowing  instructions  to  be  executed  in  parallel  in  different  stages.  This  project  implements  a  pipeline  simulator  for  the  MIPS  processor.  The  simulator  takes  a  MIPS  assembly  program  as  input  and  simulates  the  execution  of  the  program  on  a  pipelined  MIPS  processor.  The  simulator  also  displays  the  state  of  the  processor  at  each  clock  cycle  and  the  contents  of  the  registers  and  memory  at  the  end  of  the  execution  of  the  program.

## Instructions Supported

Our MIPS five stage pipeline simulator is a discrete event simulator. The simulator supports 
various R-type and I-type instructions like: ADD, SUB, AND, OR, XOR, NOR, SLL, SRl, MULT, DIV, 
LW, SW and ADDI. 

## Usage

To run the simulator, run the following command:
    
    python3 simulator.py

## Features

* Single-cycle, 5-stage pipeline
* Hazard detection
* Data forwarding
* Visualization of the pipeline, registers and memory


## Authors

* **Dhyey Thummar**
* **Shruhrid Banthia**
* **Haikoo Khandor**
* **Meet Vankar**

