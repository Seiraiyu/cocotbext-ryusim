// Smoke-test DUT. Deliberately has NO `timescale directive: the unit must
// come from COCOTB_HDL_TIMEUNIT on the compile line, which is what the
// RyuSim timescale fix provides.
module dut (
    input  logic       clk,
    input  logic [7:0] data_in,
    output logic [7:0] data_out,
    output logic [7:0] count,
    output logic       tick
);
  assign data_out = data_in;

  initial begin
    count = 0;
    tick = 0;
  end

  // Free-running: period is 10 time units, i.e. 10 ns at the default 1ns unit.
  always #5 tick = ~tick;

  always @(posedge clk) count <= count + 1;
endmodule
