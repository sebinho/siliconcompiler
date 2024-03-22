module top(input clk, input reset, input[4:0] num, output reg [4:0] out);

wire [4:0] inner0;
wire [4:0] inner1;

reg [4:0] inner_reg;

binary_4_bit_adder_top adder1(.NUM1(num), .NUM2(out), .SUM(inner0));
binary_4_bit_adder_top adder2(.NUM1(inner_reg), .NUM2(out), .SUM(inner1));

always@(posedge clk) begin
    if (reset) begin
        out <= '0;
        inner_reg <= '0;
    end
    else begin
        out <= inner1;
        inner_reg <= inner0;
    end
end

endmodule