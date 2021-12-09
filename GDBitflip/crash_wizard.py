import subprocess
import os
from os import path
import ARM_CortexA9_info

""" 
this script retrieves and prints:
    A) bad instruction which caused the crash
    B) register state at crash

by parsing text file obtained from this command:

    >gdb executable_file coredump_file -batch -ex 'info registers' -ex 'disassemble' | tee gdb_out2.txt

namely gdb_out.txt, which has this structure:

[New LWP 9075]
Core was generated by `./inj_67_basicmath_small'.
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x0002d4f0 in _dl_aux_init ()
Dump of assembler code for function _dl_aux_init:
   0x0002d4e8 <+0>: stmdb   sp!, {r4, r5, r6, r7, r8, r9, r10, r11, lr}
   0x0002d4ec <+4>: movw    r3, #59616  ; 0xe8e0
=> 0x0002d4f0 <+8>: ldr r7, [r0, #0]
   0x0002d4f2 <+10>:    movt    r3, #8
   0x0002d4f6 <+14>:    sub sp, #116    ; 0x74
   0x0002d4f8 <+16>:    str r0, [r3, #0]
...
...
...
   0x0002d7f4 <+780>:   cmp r7, #0
   0x0002d7f6 <+782>:   bne.w   0x2d5b6 <_dl_aux_init+206>
   0x0002d7fa <+786>:   b.n 0x2d60e <_dl_aux_init+294>
   0x0002d7fc <+788>:   ldr r0, [sp, #16]
   0x0002d7fe <+790>:   str.w   r0, [r8]
   0x0002d802 <+794>:   b.n 0x2d618 <_dl_aux_init+304>
End of assembler dump.
r0             0x7  7
r1             0xbeb243e8   3199353832
r2             0x2405d  147549
r3             0xe8e0   59616
r4             0x10000  65536
r5             0x8cb98  576408
r6             0x8d4f8  578808
r7             0xbeb255ac   3199358380
r8             0x8d010  577552
r9             0x0  0
r10            0x0  0
r11            0x0  0
r12            0x55 85
sp             0xbeb243bc   0xbeb243bc
lr             0x246e1  149217
pc             0x2d4f0  0x2d4f0 <_dl_aux_init+8>
cpsr           0x20000030   536870960
fpscr          0x0  0
...
...


"""

def crash_reporter(PID_l, 
                   exitcode_l, 
                   mem_mapping_l,
                   report_filename,
                   c_prog_name):
    
    binary_name = c_prog_name.split("/")[-1]
    
    ########## Clearing crash doctor data folders ##########


    if (path.exists("./crash_logs/")):
        for filename in os.listdir("./crash_logs/"):
            filepath = ""
            filepath = os.path.join("./crash_logs/", filename)
            os.remove(filepath)
    else:
        print("\tCreated ./crash_logs/ !")
        os.mkdir("./crash_logs/")  

    if not path.exists("./crash_reports/"):
        os.mkdir("./crash_reports/")

    if path.exists(report_filename):
        os.remove(report_filename)


    ########## CRASH Wizard Execution ##########

    print("\n\n\tC R A S H    W I Z A R D")

    for i in range(0,len(exitcode_l)):

        if int(exitcode_l[i]) != 0 and int(exitcode_l[i]) != -15: # or == SPECIFIC_EXIT_CODE to filter specific exit codes
        #if (crash to be analysed) AND (I didn't SIGTERM the process)
            PID = PID_l[i]
            exitcode = exitcode_l[i]
            inj_num = i
            #print(f"Analysing crash of process #{i} with PID={PID} exited with {exitcode}")


            #       ################## RETRIEVING GDB ANALYSIS LOG ##################
            crash_log_filename = f"./crash_logs/gdb_crash_log_{inj_num}_{binary_name}.log"

            # core dump is auto generated by gdb inner_script.py
            coredump_filename = f"./core_dumps/cdump_{binary_name}_inj{i}.dump" 
        
            # Creating support copy of binary 
            subprocess.run(f"cp {c_prog_name} {c_prog_name}_inj{i}",shell=True)
            
            executable_filename = f"{c_prog_name}_inj{i}"
            cmd2 = f"gdb {executable_filename} {coredump_filename} -batch -ex 'disassemble' -ex 'info all-registers' -ex 'maintenance info sections'"
            proc2 = subprocess.Popen(cmd2,shell=True,stdout=open(crash_log_filename,"w"),stderr=subprocess.DEVNULL)
            proc2.wait()

            # Removing support copy of binary 
            subprocess.run(f"rm {c_prog_name}_inj{i}",shell=True)




            print(f"\t\t\\-> CRASH_LOG at {crash_log_filename}")


            #       ################## PARSING GDB DEBUG LOG ##################
            with open(report_filename,"a+") as report:


                #print(f"\n--------------INJ_NUM={inj_num}--------------")
                report.write(f"\n\n---------------------INJ_NUM={inj_num}----EXITCODE={exitcode}({ARM_CortexA9_info.ec_dict[exitcode]})---------------------")
                
                # A) writing memory mapping of process
                report.write("\nMemory mapping at runtime:\n")
                report.write(f"\n{mem_mapping_l[i]}")

                # B) retrieve bad instruction
                with open(crash_log_filename, errors = 'replace') as f_in:    # errors = 'replace' to handle undecodable chars and replace them with '?'
                    FOUND_BAD_INSTR = False    
                    for line in f_in:
                        if not FOUND_BAD_INSTR:
                            #bad instruction line begins with "=>"
                            if line.split(" ")[0] == "=>":
                                #print(f"Bad Instruction:\n\n\t{line}")
                                report.write(f"\nBad Instruction:\n\t{line}")
                                FOUND_BAD_INSTR = True
                        else:
                            pass
                    if not FOUND_BAD_INSTR:
                        #print(f"Bad Instruction:\n\n\tCouldn't disassemble! See registers below.\n")
                        report.write(f"\nBad Instruction:\n\tCouldn't disassemble! See registers below.\n")


                # C) retrieving register state AND sections 
                with open(crash_log_filename, errors = 'replace') as f_in:    # errors = 'replace' to handle undecodable chars and replace them with '?'
                    FOUND_REG = False
                    for line1 in f_in:  
                        if not FOUND_REG:
                            # registers begin with line "r0 ...""
                            if line1.split(" ")[0] == "r0":

                                #print("Registers state:\n")
                                report.write("\nRegisters state:\n")
                                cnt = 1
                                FOUND_REG = True

                        if FOUND_REG and cnt < 17:
                            #print 18 USER registers lines
                            report.write(f"\t{line1}")
                            #print(f"\t{line1}", end="")
                            cnt += 1

                        elif FOUND_REG and (cnt >= 17) and (cnt < 17+34):
                            #print other registers lines
                            shortened_line = line1.replace(" ","")
                            report.write(f"\t{shortened_line}")
                            #print(f"\t{line1}", end="")
                            cnt += 1





    print(f"...OK\n\nSee crash report at:\n{report_filename}\n\n")