addi $t0, $zero, 0
sw $t0, 0($zero)
addi $t1, $zero, 240
sw $t1, 4($zero)
add $t3, $t0, $t1
lw $t4, 4($zero)
mult $t5, $t4, $t3
sw $t5, 8($zero)
lw $s0, 8($zero)
addi, $s1, $zero, 61200
addi $s7, $zero, 1
beq $s0, $s1, 1
addi $s7, $s7, 1