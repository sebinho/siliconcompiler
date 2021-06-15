//#############################################################################
//# Function: Padring Power-On-Control Cell                                   #
//#############################################################################
//# Author Silicon Compiler Authors                                           #
//#############################################################################

module asic_iopoc
  #(parameter TYPE  = "SOFT", // SOFT or PRIVATE PROPERTY
    parameter DIR  = "N"      // N,E,W,S
    )
(
 //feed through signals
 inout 	vddio, // io supply
 inout 	vssio, // io ground
 inout 	vdd, // core supply
 inout 	vss, // common ground
 inout 	poc // power-on-ctrl 
 );


endmodule




   