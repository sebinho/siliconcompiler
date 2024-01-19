
module _dsp_block_ (
    A,
    B,
    Y
);

    parameter A_SIGNED = 0;
    parameter B_SIGNED = 0;
    parameter A_WIDTH = 1;
    parameter B_WIDTH = 1;
    parameter Y_WIDTH = 1;

    (* force_downto *)
    input [A_WIDTH-1:0] A;
    (* force_downto *)
    input [B_WIDTH-1:0] B;
    (* force_downto *)
    output [Y_WIDTH-1:0] Y;

    dsp_mult _TECHMAP_REPLACE_ (
        .A(A),
        .B(B),
        .Y(Y)
    );


endmodule  // tech_multiplier
