# FactorioThroughputPlanner
Script for computing building proportions for Factorio builds.

Usage example for computing build requirements for "Green Science Packs" at a rate of 1.0 produced per second: 

```bash
./planner.py "Green Science Pack" 1
```
This produces the output:

```
Desired product: Green Science Pack
Desired throughput: 1.0
Solution amounts:
Iron Plate:     28.0x Furnace    = 16.0 units/second
Iron Gear Wheel:        2.0x Assembler   = 3.0 units/second
Copper Ore:     6.0x Mine        = 3.0 units/second
Inserter:       1.0x Assembler   = 1.5 units/second
Copper Cable:   1.0x Assembler   = 3.0 units/second
Iron Ore:       32.0x Mine       = 16.0 units/second
Green Science Pack:     8.0x Assembler   = 1.0 units/second
Transport Belt: 1.0x Assembler   = 3.0 units/second
Green Circuit:  1.0x Assembler   = 1.5 units/second
Copper Plate:   6.0x Furnace     = 3.42857142857 units/second
```
