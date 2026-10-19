
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer


async def tick(dut):
    """等待时钟上升沿，并给 RTL 留出更新时间。"""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")


@cocotb.test()
async def test_fifo(dut):
    """验证 FIFO 复位、单次读写、满空状态和数据顺序。"""

    dut.rst.value = 1
    dut.wr_en.value = 0
    dut.rd_en.value = 0
    dut.din.value = 0

    cocotb.start_soon(
        Clock(dut.clk, 10, unit="ns").start()
    )

    # 1. Reset
    await tick(dut)
    assert int(dut.empty.value) == 1, "FIFO reset: empty should be 1"
    assert int(dut.full.value) == 0, "FIFO reset: full should be 0"

    await FallingEdge(dut.clk)
    dut.rst.value = 0

    # 2. Read while empty: FIFO should remain empty
    dut.rd_en.value = 1
    await tick(dut)
    assert int(dut.empty.value) == 1, "Reading empty FIFO changed its state"

    await FallingEdge(dut.clk)
    dut.rd_en.value = 0

    # 3. Write one value, then read it back
    dut.wr_en.value = 1
    dut.din.value = 0xA5
    await tick(dut)

    await FallingEdge(dut.clk)
    dut.wr_en.value = 0
    dut.rd_en.value = 1
    await tick(dut)

    assert int(dut.dout.value) == 0xA5, (
        f"Readback mismatch: expected 0xA5, got {int(dut.dout.value):#04x}"
    )
    assert int(dut.empty.value) == 1, "FIFO should be empty after reading one item"

    # 4. Fill all 16 entries
    await FallingEdge(dut.clk)
    dut.rd_en.value = 0
    dut.wr_en.value = 1

    for i in range(16):
        dut.din.value = i
        await tick(dut)
        await FallingEdge(dut.clk)

    dut.wr_en.value = 0

    assert int(dut.full.value) == 1, "FIFO should be full after 16 writes"
    assert int(dut.empty.value) == 0, "Full FIFO should not be empty"

    # 5. Extra write while full must be ignored
    dut.wr_en.value = 1
    dut.din.value = 0xFF
    await tick(dut)

    assert int(dut.full.value) == 1, "FIFO full flag unexpectedly cleared"

    # 6. Read all 16 values in FIFO order
    await FallingEdge(dut.clk)
    dut.wr_en.value = 0
    dut.rd_en.value = 1

    for i in range(16):
        await tick(dut)
        actual = int(dut.dout.value)
        assert actual == i, (
            f"FIFO order mismatch at index {i}: expected {i:#04x}, got {actual:#04x}"
        )
        await FallingEdge(dut.clk)

    dut.rd_en.value = 0
    await Timer(1, unit="ns")

    assert int(dut.empty.value) == 1, "FIFO should be empty after draining"

    dut._log.info("PASS: all cocotb FIFO tests passed")
