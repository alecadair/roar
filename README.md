
# ROAR
The Robust and Optimal Analog Reuse (ROAR) flow/tool is developed to enable a GUI based approach to the C/ID and gm/ID (I like to say Inverse ID) analog circuit design methodologies. This software enables the the ability to design, optimize, and generate process/technology agnostic design scripts in a graphical yet automated fashion.

## Installation

To set up the ROAR environment, follow these steps:

1. **Install dependencies**  
   First, install the required Python dependencies using pip. Run the following command:

   ```bash
   pip install -r requirements.txt
   ```

2. **Run make to create environment**  
   Second, run make in the top level of your local copy of this repository:

   ```bash
   make
   ```
   This generates a file called roar_env.csh

3. **Set environmental variables**  
   After installing the dependencies and running make, you need to source the environment configuration file generated from make. To do this, run:

   ```bash
   source roar_env.csh
   ```

   This will configure the environment variables needed for ROAR to function properly.

## Purpose

ROAR is designed to enable and optimize gm/id and c/id based analog circuit design. The primary goal of this software is to streamline the process of analog circuit design, making it easier to optimize and reuse existing designs through an efficient and automated workflow.
