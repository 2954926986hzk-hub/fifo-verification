# Synchronous FIFO RTL Design and Verification

## 1. Project Overview

This project implements and verifies a synchronous FIFO using Verilog RTL, Icarus Verilog, and cocotb.

## 2. Design Parameters

- Data width: 8 bits
- FIFO depth: 16 entries
- Clock: single clock
- Reset: synchronous reset
- Status flags: `full` and `empty`

## 3. Project Structure

```text
fifo-demo/
├── rtl/
│   └── sync_fifo.v
├── sim/
│   ├── tb_sync_fifo.v
│   ├── test_sync_fifo.py
│   └── test_sync_fifo_basic.py
├── Makefile
└── README.md
```

## 4. Verification Features

- Reset behavior
- Single write and read
- Empty-read handling
- Full-write handling
- FIFO data ordering
- Pointer wraparound
- Python reference queue
- Randomized read/write operations

## 5. Requirements

- Python 3
- cocotb
- Icarus Verilog
- GNU Make

## 6. Run the Tests

Activate the Python virtual environment:

```bash
source .venv/bin/activate
```

Run the simulation:

```bash
make
```

The test passes when cocotb reports zero failures.

## 7. Learning Objectives

This project demonstrates basic RTL design, simulation-based verification, Python-driven test automation, and regression testing.

## 8. Future Improvements

- Add simultaneous read/write corner-case tests
- Add functional coverage statistics
- Improve parameter checking
- Evaluate FPGA synthesis and timing
