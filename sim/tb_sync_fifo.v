
`timescale 1ns/1ps

module tb_sync_fifo;

    reg clk = 0;
    reg rst = 1;
    reg wr_en = 0;
    reg rd_en = 0;
    reg [7:0] din = 0;

    wire [7:0] dout;
    wire full;
    wire empty;

    integer errors = 0;
    integer i;

    sync_fifo dut (
        .clk(clk),
        .rst(rst),
        .wr_en(wr_en),
        .rd_en(rd_en),
        .din(din),
        .dout(dout),
        .full(full),
        .empty(empty)
    );

    always #5 clk = ~clk;

    task tick;
        begin
            @(posedge clk);
            #1;
        end
    endtask

    initial begin
        $dumpfile("sim/fifo.vcd");
        $dumpvars(0, tb_sync_fifo);

        // 1. Reset check
        tick;
        if (empty !== 1'b1 || full !== 1'b0) begin
            $display("FAIL: reset flags");
            errors = errors + 1;
        end

        @(negedge clk);
        rst = 0;

        // 2. Empty read must not change occupancy
        rd_en = 1;
        tick;
        if (empty !== 1'b1) begin
            $display("FAIL: empty read changed FIFO state");
            errors = errors + 1;
        end

        @(negedge clk);
        rd_en = 0;

        // 3. Write and read back one value
        wr_en = 1;
        din = 8'hA5;
        tick;

        @(negedge clk);
        wr_en = 0;
        rd_en = 1;
        tick;

        if (dout !== 8'hA5) begin
            $display("FAIL: readback expected A5, got %h", dout);
            errors = errors + 1;
        end

        if (empty !== 1'b1) begin
            $display("FAIL: FIFO should be empty after read");
            errors = errors + 1;
        end

        @(negedge clk);
        rd_en = 0;

        // 4. Fill FIFO to capacity
        for (i = 0; i < 16; i = i + 1) begin
            @(negedge clk);
            wr_en = 1;
            din = i;
            tick;
        end

        @(negedge clk);
        wr_en = 0;

        if (full !== 1'b1 || empty !== 1'b0) begin
            $display("FAIL: full flag");
            errors = errors + 1;
        end

        // 5. Attempt one extra write
        din = 8'hFF;
        wr_en = 1;
        tick;

        if (full !== 1'b1) begin
            $display("FAIL: extra write changed full flag");
            errors = errors + 1;
        end

        // 6. Read back all 16 values in order
        @(negedge clk);
        wr_en = 0;
        rd_en = 1;

        for (i = 0; i < 16; i = i + 1) begin
            tick;
            if (dout !== i[7:0]) begin
                $display(
                    "FAIL: index=%0d expected=%h actual=%h",
                    i, i[7:0], dout
                );
                errors = errors + 1;
            end
        end

        @(negedge clk);
        rd_en = 0;

        if (empty !== 1'b1) begin
            $display("FAIL: empty flag after draining");
            errors = errors + 1;
        end

        if (errors == 0)
            $display("PASS: all FIFO tests passed");
        else
            $display("FAIL: total errors = %0d", errors);

        $finish;
    end

endmodule
