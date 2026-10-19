
module sync_fifo #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_WIDTH = 4
) (
    input  wire                  clk,
    input  wire                  rst,
    input  wire                  wr_en,
    input  wire                  rd_en,
    input  wire [DATA_WIDTH-1:0] din,
    output reg  [DATA_WIDTH-1:0] dout,
    output wire                  full,
    output wire                  empty
);

    reg [DATA_WIDTH-1:0] mem [0:DEPTH-1];

    reg [ADDR_WIDTH-1:0] wr_ptr;
    reg [ADDR_WIDTH-1:0] rd_ptr;
    reg [ADDR_WIDTH:0]   count;

    assign full  = (count == DEPTH);
    assign empty = (count == 0);

    always @(posedge clk) begin
        if (rst) begin
            wr_ptr <= 0;
            rd_ptr <= 0;
            count  <= 0;
            dout   <= 0;
        end else begin

            // Write data when FIFO is not full.
            if (wr_en && !full) begin
                mem[wr_ptr] <= din;
                wr_ptr <= (wr_ptr == DEPTH-1) ? 0 : wr_ptr + 1'b1;
            end

            // Read data when FIFO is not empty.
            if (rd_en && !empty) begin
                dout <= mem[rd_ptr];
                rd_ptr <= (rd_ptr == DEPTH-1) ? 0 : rd_ptr + 1'b1;
            end

            // Update occupancy count.
            case ({wr_en && !full, rd_en && !empty})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
        end
    end

endmodule
