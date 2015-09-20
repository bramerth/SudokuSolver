# SudokuSolver
A program to solve Sudoku puzzles

## Usage
* Solve the puzzle in samples/evil.txt:

  `python sudoku.py samples/evil.txt`
  
  The expected format of the input file is a nine line file with nine characters per line. 1-9 represent solved cells while "-" represents a blank. 

* Solve a random hard puzzle from websudoku.com:

  `python sudoku.py --level 3`

Verbose output about the algorithm's choices can be enabled with -v.
