# Iterative Solver — Example: Two-Stage OTA

## Problem

In a two-stage OTA the output capacitance of Stage 1 is part of the load
that Stage 2 presents back to Stage 1. Similarly, the input capacitance of
Stage 2 depends on the bias point of its transistors, which in turn depends
on how much current it needs to drive *its* load — which includes the
parasitic drain capacitance of Stage 1's output devices.

These mutual dependencies create a **cycle** in the design equations that
cannot be resolved in a single pass. The iterative solver repeatedly
evaluates the equations, feeding each pass's output back as the next pass's
input, until the values converge.

---

## Circuit Setup

Assume a two-stage Miller OTA with the following instances in the
**Instance Table** of the Design Editor:

| Instance | Description               |
|----------|---------------------------|
| M1       | Stage 1 diff-pair NMOS    |
| M3       | Stage 1 PMOS load         |
| M5       | Stage 2 common-source NMOS|
| M7       | Stage 2 PMOS load         |

Each instance has its own corner selection in the Instance Table (e.g.
`SKY130A > n_01v8 > 150 > nfettt27` for M1).

---

## Step 1: Write the Design Equations

In the **Expression Editor**, enter the following expressions. The key
insight is that `Cload1` (the load seen by Stage 1) depends on a lookup
from Stage 2 (`cgs:M5`), and `Cload2` (the load seen by Stage 2) depends
on a lookup from Stage 1 (`cdd:M3`).

| Symbol   | Expression                                      | Notes                                  |
|----------|-------------------------------------------------|----------------------------------------|
| `GBW`    | `100e6`                                         | Target GBW: 100 MHz                    |
| `CL`     | `1e-12`                                         | External load: 1 pF                    |
| `kgm1`   | `kgm:M1`                                        | gm/Id lookup for M1                    |
| `cgs5`   | `cgs:M5`                                        | Cgs lookup for M5                      |
| `cdd3`   | `cdd:M3`                                        | Cdd lookup for M3                      |
| `cdd5`   | `cdd:M5`                                        | Cdd lookup for M5                      |
| `cgd3`   | `cgd:M3`                                        | Cgd lookup for M3 (Miller cap)         |
| `Cload1` | `abs(cgs5) + abs(cdd3) + abs(cgd3)`             | **Stage 1 output load** ← depends on M5|
| `Cload2` | `abs(cdd5) + CL`                                | **Stage 2 output load** ← depends on M5|
| `gm1`    | `2 * 3.14159 * GBW * Cload1`                    | Required gm for Stage 1                |
| `Id1`    | `gm1 / kgm1`                                    | Drain current for Stage 1              |
| `gm5`    | `2 * 3.14159 * GBW * 3 * Cload2`                | Required gm for Stage 2 (3× BW margin)|
| `kgm5`   | `kgm:M5`                                        | gm/Id lookup for M5                    |
| `Id5`    | `gm5 / kgm5`                                    | Drain current for Stage 2              |

### Why this creates a cycle

```
Cload1 depends on cgs5 (lookup from M5)
   └→ M5's bias point depends on Id5
       └→ Id5 = gm5 / kgm5
           └→ gm5 depends on Cload2
               └→ Cload2 depends on cdd5 (lookup from M5)

Meanwhile cgs5 and cdd5 are both looked up from M5's LUT,
which is indexed by the sweep current. The sweep current
itself is shaped by Id5, closing the loop.
```

Without the iterative solver, ROAR would reject these equations with
*"Error: The equations have cyclical dependencies."*

---

## Step 2: Open the Iterative Solver

1. Go to **Solver → Iterative Solver...** in the menu bar.
2. The **Iterative Solver Settings** dialog opens.

---

## Step 3: Configure the Solver

1. **Check** *"Enable Iterative Solver"*.

2. Set parameters (or leave defaults):

   | Parameter     | Value  | Meaning                                       |
   |---------------|--------|-----------------------------------------------|
   | **Max Iter**  | `50`   | Stop after 50 iterations even if not converged |
   | **Tol**       | `1e-6` | Converge when max relative change < 1e-6       |
   | **Damp**      | `1.0`  | No damping (pure fixed-point iteration)         |

   > **Tip:** If the solver oscillates and doesn't converge, lower **Damp**
   > to 0.5–0.8. This blends old and new values:
   > `x = damp × x_new + (1 − damp) × x_old`

3. Click **"Detect Cycles"**.

   The solver analyzes the dependency graph and reports something like:

   > *Found 4 cycle variable(s)*

   The **Initial Guesses** table is auto-populated with the cycle
   variables (e.g. `Cload1`, `cgs5`, `cdd3`, `cdd5`).

4. Enter reasonable initial guesses:

   | Symbol   | Initial Value |
   |----------|---------------|
   | `Cload1` | `1e-13`       |
   | `cgs5`   | `5e-14`       |
   | `cdd3`   | `2e-14`       |
   | `cdd5`   | `2e-14`       |

   > **Tip:** Order-of-magnitude estimates are sufficient. The solver
   > converges from a wide range of starting points for well-conditioned
   > systems. If you have no idea, leave them at `0` — the solver will
   > still converge in most cases, it may just take a few more iterations.

5. Click **Close** (settings are preserved).

---

## Step 4: Refresh the Graphs

1. Switch a Lookup Window to **Design Eqs** mode.
2. Select axes (e.g. X = `kgm1`, Y = `Id1`).
3. Click the **🔄 Refresh** button in the Design Editor.

The status bar at the bottom of the main window will show convergence info:

```
Iterative solver: ✓ Converged after 8 iteration(s), max Δ = 4.231e-09
```

If it reports **✗ NOT converged**, try:
- Increasing **Max Iter**
- Lowering **Damp** (e.g. 0.7)
- Providing better initial guesses

---

## Step 5: Add Constraints (Optional)

In the **Constraint Editor**, you can add constraints that filter the
solution space. These are evaluated after convergence:

| Symbol         | Constraint Expression  | Meaning                       |
|----------------|------------------------|-------------------------------|
| `bw_ok`        | `GBW > 80e6`           | Keep only points above 80 MHz |
| `power_limit`  | `Id1 + Id5 < 500e-6`   | Total current < 500 µA        |

---

## Step 6: Save the Design

Click **Save** in the Design Editor to write all expressions, constraints,
instance mappings, and iterative solver settings to a `.json` file.
Everything is restored when you **Load** the file later.

The iterative solver settings are also included in **File → Save State**
for full application state snapshots.

---

## Summary

| What                    | Where                                    |
|-------------------------|------------------------------------------|
| Open iterative solver   | **Solver → Iterative Solver...**         |
| Enable it               | Check *"Enable Iterative Solver"*        |
| Find cycle variables    | Click **"Detect Cycles"**                |
| Set initial guesses     | Edit the **Initial Guesses** table       |
| Run the solver          | Click **🔄 Refresh** in the Design Editor|
| Check convergence       | Read the **status bar** message          |
| Tune convergence        | Adjust **Damp**, **Max Iter**, **Tol**   |

